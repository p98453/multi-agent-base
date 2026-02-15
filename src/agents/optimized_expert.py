#!/usr/bin/env python3
"""
优化后的专家智能体（Optimized Expert Agent）

本模块实现了多智能体系统中的专家分析组件。每个专家智能体对应一个特定的安全领域，
负责对路由到本领域的告警进行深度分析。

核心职责：
1. 根据自身专家类型（expert_type），使用领域专用的提示词模板生成 Prompt
2. 调用远程 LLM（大语言模型）进行智能分析，获取结构化的 JSON 分析结果
3. 解析 LLM 返回的 JSON 响应，提取攻击技术、风险评分、防御建议等信息
4. 当 LLM 调用失败时，降级到基于规则的本地分析方案，确保系统可用性

设计亮点：
- 提示词工程：每种攻击类型有精心设计的 Prompt 模板，引导 LLM 输出结构化 JSON
- 优雅降级：LLM 不可用时自动切换到规则引擎，保证分析服务不中断
- 性能监控：记录 LLM 调用耗时、输入/输出 token 数量等性能指标
"""
import time
import json
from typing import Dict, Any
from src.models.llm_inference import get_llm_inference
from src.utils.structured_logger import get_logger

class OptimizedExpertAgent:
    """专家智能体 - 精简版
    
    每个实例代表一个特定领域的安全专家，支持以下三种专家类型：
    - web_attack: Web安全专家（SQL注入、XSS、命令注入等）
    - vulnerability_attack: 漏洞利用专家（CVE、Exploit等）
    - illegal_connection: 网络连接专家（C2通信、僵尸网络等）
    """
    
    def __init__(self, expert_type: str):
        """初始化专家智能体
        
        Args:
            expert_type: 专家类型标识，决定使用哪套提示词模板进行分析。
                         可选值：'web_attack', 'vulnerability_attack', 'illegal_connection'
        """
        self.expert_type = expert_type         # 记录该专家的领域类型
        self.logger = get_logger()             # 获取全局结构化日志记录器
        
        # 专家提示词模板字典
        # 每个模板都指示 LLM 扮演特定领域的安全专家角色，并要求以 JSON 格式返回分析结果
        # 模板中使用 {attack_type}、{payload} 等占位符，在生成 Prompt 时被实际告警数据替换
        # 注意：模板中的 {{ 和 }} 是 Python str.format() 中对花括号的转义写法，
        #       渲染后会变成单个 { 和 }，作为 JSON 示例展示给 LLM
        self.prompt_templates = {
            'web_attack': """你是一名资深Web安全分析专家，擅长识别OWASP Top 10及各类Web攻击技术。

## 告警信息
- 攻击类型: {attack_type}
- 攻击载荷: {payload}
- 攻击来源IP: {source_ip}
- 目标服务IP: {target_ip}

## 分析要求
请按以下步骤进行分析：
1. 识别攻击技术：判断具体攻击手法（如SQL注入、XSS、CSRF、SSRF、文件包含、目录遍历等），并关联MITRE ATT&CK技术编号
2. 评估风险等级：根据以下标准给出0-10的风险评分
   - 9-10 (高危): 可直接获取系统权限、窃取大量敏感数据、远程代码执行
   - 6-8 (中危): 可窃取部分数据、绕过认证、影响服务可用性
   - 1-5 (低危): 信息泄露、低危配置问题、需要特殊条件才能利用
3. 给出针对性的防御建议（至少3条，按优先级排列）

请严格以JSON格式返回（不要附加其他内容）:
{{
    "attack_technique": "具体攻击技术名称（如：基于UNION的SQL注入）",
    "risk_score": 8.5,
    "threat_level": "高危",
    "recommendations": ["最高优先级建议", "次优先级建议", "补充建议"],
    "analysis": "详细分析：包括攻击原理、潜在影响范围、攻击者意图判断"
}}""",
            
            'vulnerability_attack': """你是一名资深漏洞利用分析专家，熟悉CVE漏洞库和常见漏洞利用框架（Metasploit、Cobalt Strike等）。

## 告警信息
- 攻击类型: {attack_type}
- 攻击载荷: {payload}
- 攻击来源IP: {source_ip}
- 目标服务IP: {target_ip}

## 分析要求
请按以下步骤进行分析：
1. 漏洞识别：判断载荷所利用的具体漏洞类型（如缓冲区溢出、命令注入、反序列化、文件上传等），尝试关联已知CVE编号
2. 利用链分析：分析攻击者的利用路径和攻击意图（提权、持久化、横向移动等）
3. 评估风险等级：根据以下标准给出0-10的风险评分
   - 9-10 (高危): 远程代码执行、权限提升到root/SYSTEM、无需认证即可利用
   - 6-8 (中危): 需认证后才可利用、本地特权提升、信息泄露
   - 1-5 (低危): 拒绝服务、需复杂前置条件、利用价值有限
4. 给出修复和加固建议（至少3条，按优先级排列）

请严格以JSON格式返回（不要附加其他内容）:
{{
    "attack_technique": "具体漏洞利用技术名称（如：Apache Log4j JNDI远程代码执行）",
    "risk_score": 8.0,
    "threat_level": "高危",
    "recommendations": ["紧急修复建议", "加固建议", "检测建议"],
    "analysis": "详细分析：包括漏洞原理、利用条件、影响范围、攻击阶段判断"
}}""",
            
            'illegal_connection': """你是一名资深网络威胁情报分析专家，擅长识别C2通信、数据外泄、横向移动等异常网络行为。

## 告警信息
- 攻击类型: {attack_type}
- 连接载荷/流量特征: {payload}
- 源IP: {source_ip}
- 目标IP: {target_ip}

## 分析要求
请按以下步骤进行分析：
1. 连接行为分类：判断连接类型（C2通信、反弹Shell、数据外泄、隧道通信、DGA域名、横向移动等）
2. 威胁归因：分析通信特征，判断是否关联已知恶意组织或攻击框架（APT组织、Cobalt Strike、Sliver等）
3. 评估风险等级：根据以下标准给出0-10的风险评分
   - 9-10 (高危): 已建立C2通道、正在进行数据外泄、内网横向移动
   - 6-8 (中危): DNS隧道、可疑心跳通信、加密异常流量
   - 1-5 (低危): 扫描探测、低频可疑连接、误报可能性较高
4. 给出应急响应建议（至少3条，按紧急程度排列）

请严格以JSON格式返回（不要附加其他内容）:
{{
    "attack_technique": "具体威胁类型（如：Cobalt Strike Beacon C2通信）",
    "risk_score": 9.0,
    "threat_level": "高危",
    "recommendations": ["紧急响应措施", "取证分析建议", "长期防御建议"],
    "analysis": "详细分析：包括通信模式特征、威胁归因、潜在攻击阶段（初始访问/持久化/数据外泄）"
}}"""
        }
    
    async def analyze(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行专家级威胁分析（异步方法）
        
        这是专家智能体的核心入口方法，完整的分析流程：
        1. 根据 expert_type 生成对应的 Prompt
        2. 调用远程 LLM API 获取分析结果
        3. 解析 LLM 的 JSON 响应
        4. 若 LLM 调用失败，降级到基于规则的本地分析
        5. 记录分析日志（包括性能指标）
        
        降级机制说明：
        - 当 LLM API 不可用（网络超时、API Key 无效等）时，
          系统会自动切换到 _rule_based_analysis() 方法
        - 规则分析基于关键词匹配，虽然不如 LLM 智能，但能保证基本的分析能力
        
        Args:
            alert_data: 告警数据字典，包含 attack_type, payload, source_ip, target_ip 等字段
            
        Returns:
            dict: 分析结果，包含 attack_technique, risk_score, threat_level, 
                  recommendations, analysis, processing_time_ms, expert_type 等
        """
        start_time = time.time()
        
        # 步骤1: 根据专家类型和告警数据生成 LLM 提示词
        prompt = self._generate_prompt(alert_data)
        
        # 步骤2: 调用 LLM 进行智能分析
        try:
            # 获取全局 LLM 推理实例（单例模式，避免重复初始化）
            llm = get_llm_inference()
            
            # 简化的 token 数量估算：以空格分词近似计算输入 token 数
            # 注意：这不是精确的 tokenizer 计算，仅用于日志统计
            input_tokens = len(prompt.split())
            
            # 调用远程 LLM API 生成分析结果
            # max_new_tokens=300: 限制输出长度，防止响应过长
            # temperature=0.3: 较低的温度值使输出更确定、更聚焦，适合安全分析场景
            llm_start = time.time()
            response = await llm.generate_response(
                prompt,
                max_new_tokens=512,
                temperature=0.3
            )
            llm_time_ms = int((time.time() - llm_start) * 1000)
            
            # 估算输出 token 数量
            output_tokens = len(response.split())
            
            # 记录 LLM 调用性能日志，便于后续分析 API 调用成本和延迟
            self.logger.log("llm_inference", {
                "expert_type": self.expert_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "processing_time_ms": llm_time_ms,
                "model": "Qwen (remote API)"
            })
            
            # 步骤3: 解析 LLM 的 JSON 格式响应
            result = self._parse_response(response)
            
        except Exception as e:
            # LLM 调用失败时的降级处理
            # 记录错误日志（级别为 ERROR），便于排查 API 连接问题
            self.logger.log("llm_inference_error", {
                "expert_type": self.expert_type,
                "error": str(e)
            }, level="ERROR")
            
            # 降级到基于规则的本地分析（不依赖 LLM，纯关键词匹配）
            result = self._rule_based_analysis(alert_data)
        
        # 计算整体分析耗时（包括 Prompt 生成 + LLM 调用 + 结果解析）
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 记录专家分析完成的日志
        self.logger.log("expert_analysis", {
            "expert_type": self.expert_type,
            "attack_type": result.get('attack_technique', 'unknown'),
            "risk_score": result.get('risk_score', 5.0),
            "processing_time_ms": processing_time_ms
        })
        
        # 在分析结果中附加性能信息和专家类型标识
        result['processing_time_ms'] = processing_time_ms
        result['expert_type'] = self.expert_type
        
        return result
    
    def _generate_prompt(self, alert_data: Dict[str, Any]) -> str:
        """根据专家类型和告警数据生成 LLM 提示词
        
        从 prompt_templates 中选取对应专家类型的模板，
        使用 str.format() 将告警数据中的各字段填充到模板占位符中。
        
        安全措施：
        - 使用 dict.get() 提供默认值，防止字段缺失导致 KeyError
        - payload 字段截取前 500 字符，防止超长载荷导致 Prompt 过大
        
        Args:
            alert_data: 告警数据字典
            
        Returns:
            str: 填充完成的完整提示词字符串
        """
        # 获取对应专家类型的模板，如果类型不存在则回退到 web_attack 模板
        template = self.prompt_templates.get(self.expert_type, self.prompt_templates['web_attack'])
        
        # 用告警数据填充模板中的占位符
        return template.format(
            attack_type=alert_data.get('attack_type', 'unknown'),
            payload=alert_data.get('payload', '')[:500],  # 限制 payload 长度为500字符，避免 Prompt 过长
            source_ip=alert_data.get('source_ip', 'unknown'),
            target_ip=alert_data.get('target_ip', 'unknown')
        )
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 返回的响应文本，尝试提取其中的 JSON 结构
        
        LLM 的输出通常是混合文本，其中嵌套了 JSON 格式的分析结果。
        本方法通过定位第一个 '{' 和最后一个 '}' 来提取 JSON 子串。
        
        解析策略：
        1. 找到响应中 JSON 对象的起止位置（最外层的 { 和 }）
        2. 提取 JSON 子串并使用 json.loads() 解析
        3. 如果解析失败（格式错误、无 JSON 等），返回默认的基础分析结构
        
        Args:
            response: LLM 的原始响应文本
            
        Returns:
            dict: 解析后的分析结果字典
        """
        try:
            # 定位 JSON 对象的边界：第一个 '{' 到最后一个 '}'
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                result = json.loads(json_str)
                return result
        except:
            pass  # JSON 解析失败，使用下方的默认返回值
        
        # 解析失败时返回默认结构，保证调用方始终能获得有效的分析结果
        return {
            'attack_technique': 'unknown',
            'risk_score': 5.0,                      # 默认中等风险评分
            'analysis': response[:200],              # 截取 LLM 原始响应的前200字符作为分析内容
            'recommendations': ['提高警惕', '进一步分析']  # 通用的默认建议
        }
    
    def _rule_based_analysis(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于规则的分析（LLM 调用失败时的降级方案）
        
        当远程 LLM API 不可用时，使用本地关键词匹配规则进行基础威胁分析。
        虽然不如 LLM 的分析精准，但能保证系统在 API 故障时仍能提供基本服务。
        
        匹配逻辑：
        - 按优先级依次匹配 SQL注入 → XSS → 命令注入 → C2通信
        - 每种攻击类型有对应的关键词列表和预设的风险评分 + 防御建议
        - 如果所有规则都未匹配，返回默认结果（unknown, 风险评分 5.0）
        
        Args:
            alert_data: 告警数据字典
            
        Returns:
            dict: 基于规则的分析结果，格式与 LLM 分析结果保持一致
        """
        payload = alert_data.get('payload', '').lower()    # 转小写以实现大小写无关匹配
        attack_type = alert_data.get('attack_type', '').lower()
        
        risk_score = 5.0                # 默认风险评分
        technique = 'unknown'           # 默认攻击技术
        recommendations = []            # 默认防御建议列表
        
        # 规则链：按优先级依次匹配各种攻击类型
        # SQL注入特征：UNION、SELECT、DROP、INSERT、单引号注入（' or）、SQL注释（--）
        if any(kw in payload for kw in ['union', 'select', 'drop', 'insert', "' or", '-- ']):
            risk_score = 8.5
            technique = 'SQL注入'
            recommendations = ['使用参数化查询', '部署WAF', '输入验证']
        
        # XSS（跨站脚本）特征：<script>标签、javascript:协议、onerror事件、alert()函数
        elif any(kw in payload for kw in ['<script', 'javascript:', 'onerror=', 'alert(']):
            risk_score = 7.5
            technique = 'XSS跨站脚本'
            recommendations = ['输出编码', 'CSP策略', '输入过滤']
        
        # 命令注入特征：wget/curl下载、bash执行、管道符(|)、分号(;)、逻辑与(&&)
        elif any(kw in payload for kw in ['wget', 'curl', 'bash', '| ', '; ', '&& ']):
            risk_score = 9.0
            technique = '命令注入'
            recommendations = ['禁用危险函数', '白名单验证', '权限最小化']
        
        # C2通信特征：HTTP URL、PowerShell、cmd.exe
        elif any(kw in payload for kw in ['http://', 'https://', 'powershell', 'cmd.exe']):
            risk_score = 8.0
            technique = 'C2通信'
            recommendations = ['阻断可疑IP', '流量监控', '终端检测']
        
        return {
            'attack_technique': technique,
            'risk_score': risk_score,
            # 根据风险评分自动映射威胁等级：≥7 为高危，≥4 为中危，其他为低危
            'threat_level': '高危' if risk_score >= 7 else '中危' if risk_score >= 4 else '低危',
            'recommendations': recommendations,
            'analysis': f'基于规则分析识别为{technique}，风险评分{risk_score}'
        }
