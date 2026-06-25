#!/usr/bin/env python3
"""
优化后的专家智能体（Optimized Expert Agent）- LangChain 重构版

本模块实现了多智能体系统中的专家分析组件。每个专家智能体对应一个特定的安全领域，
负责对路由到本领域的告警进行深度分析。

核心职责：
1. 根据自身专家类型（expert_type），使用 LangChain ChatPromptTemplate 生成 Prompt
2. 调用远程 LLM（通过 LangChain ChatOpenAI）进行智能分析，获取结构化的 JSON 分析结果
3. 解析 LLM 返回的 JSON 响应，提取攻击技术、风险评分、防御建议等信息
4. 当 LLM 调用失败时，降级到基于规则的本地分析方案，确保系统可用性

重构要点：
- 使用 LangChain ChatPromptTemplate 替代手动 str.format() 拼接
- 使用 LangChain ChatOpenAI.ainvoke() 替代手写 httpx 异步调用
- 保留规则降级机制，确保高可用性
"""
import time
import json
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from src.models.llm_factory import get_chat_llm
from src.utils.structured_logger import get_logger


class OptimizedExpertAgent:
    """专家智能体 - LangChain 重构版

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

        # 使用 LangChain ChatPromptTemplate 构建提示词模板
        # 每个模板都指示 LLM 扮演特定领域的安全专家角色，并要求以 JSON 格式返回分析结果
        self.prompt_templates = {
            'web_attack': ChatPromptTemplate.from_messages([
                ("system", "你是一名资深Web安全分析专家，擅长识别OWASP Top 10及各类Web攻击技术。"),
                ("human", """## 告警信息
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
}}""")
            ]),

            'vulnerability_attack': ChatPromptTemplate.from_messages([
                ("system", "你是一名资深漏洞利用分析专家，熟悉CVE漏洞库和常见漏洞利用框架（Metasploit、Cobalt Strike等）。"),
                ("human", """## 告警信息
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
}}""")
            ]),

            'illegal_connection': ChatPromptTemplate.from_messages([
                ("system", "你是一名资深网络威胁情报分析专家，擅长识别C2通信、数据外泄、横向移动等异常网络行为。"),
                ("human", """## 告警信息
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
}}""")
            ])
        }

        # LangChain 输出解析器（提取纯文本内容）
        self.output_parser = StrOutputParser()

    async def analyze(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行专家级威胁分析（异步方法）

        这是专家智能体的核心入口方法，完整的分析流程：
        1. 根据 expert_type 选择对应的 ChatPromptTemplate
        2. 使用 LangChain LCEL 链式调用：prompt | llm | output_parser
        3. 解析 LLM 的 JSON 响应
        4. 若 LLM 调用失败，降级到基于规则的本地分析
        5. 记录分析日志（包括性能指标）

        Args:
            alert_data: 告警数据字典，包含 attack_type, payload, source_ip, target_ip 等字段

        Returns:
            dict: 分析结果，包含 attack_technique, risk_score, threat_level,
                  recommendations, analysis, processing_time_ms, expert_type 等
        """
        start_time = time.time()

        try:
            # 步骤1: 获取对应专家类型的 ChatPromptTemplate
            prompt = self.prompt_templates.get(
                self.expert_type,
                self.prompt_templates['web_attack']
            )

            # 步骤2: 获取 LangChain LLM 实例
            llm = get_chat_llm()

            # 步骤3: 构建 LCEL 链并异步调用
            # LCEL（LangChain Expression Language）链式调用：prompt → llm → parser
            chain = prompt | llm | self.output_parser

            # 准备输入变量
            input_vars = {
                "attack_type": alert_data.get('attack_type', 'unknown'),
                "payload": alert_data.get('payload', '')[:500],  # 限制 payload 长度
                "source_ip": alert_data.get('source_ip', 'unknown'),
                "target_ip": alert_data.get('target_ip', 'unknown'),
            }

            # 简化的 token 数量估算
            input_tokens = sum(len(v.split()) for v in input_vars.values())

            # 异步调用 LCEL 链
            llm_start = time.time()
            response = await chain.ainvoke(input_vars)
            llm_time_ms = int((time.time() - llm_start) * 1000)

            # 估算输出 token 数量
            output_tokens = len(response.split())

            # 记录 LLM 调用性能日志
            self.logger.log("llm_inference", {
                "expert_type": self.expert_type,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "processing_time_ms": llm_time_ms,
                "model": f"LangChain ChatOpenAI ({llm.model_name})"
            })

            # 步骤4: 解析 LLM 的 JSON 格式响应
            result = self._parse_response(response)

        except Exception as e:
            # LLM 调用失败时的降级处理
            self.logger.log("llm_inference_error", {
                "expert_type": self.expert_type,
                "error": str(e)
            }, level="ERROR")

            # 降级到基于规则的本地分析
            result = self._rule_based_analysis(alert_data)

        # 计算整体分析耗时
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

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 返回的响应文本，尝试提取其中的 JSON 结构

        LLM 的输出通常是混合文本，其中嵌套了 JSON 格式的分析结果。
        本方法通过定位第一个 '{' 和最后一个 '}' 来提取 JSON 子串。

        Args:
            response: LLM 的原始响应文本

        Returns:
            dict: 解析后的分析结果字典
        """
        try:
            # 定位 JSON 对象的边界
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                result = json.loads(json_str)
                return result
        except:
            pass

        # 解析失败时返回默认结构
        return {
            'attack_technique': 'unknown',
            'risk_score': 5.0,
            'analysis': response[:200],
            'recommendations': ['提高警惕', '进一步分析']
        }

    def _rule_based_analysis(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """基于规则的分析（LLM 调用失败时的降级方案）

        当远程 LLM API 不可用时，使用本地关键词匹配规则进行基础威胁分析。

        Args:
            alert_data: 告警数据字典

        Returns:
            dict: 基于规则的分析结果
        """
        payload = alert_data.get('payload', '').lower()
        attack_type = alert_data.get('attack_type', '').lower()

        risk_score = 5.0
        technique = 'unknown'
        recommendations = []

        # SQL注入特征
        if any(kw in payload for kw in ['union', 'select', 'drop', 'insert', "' or", '-- ']):
            risk_score = 8.5
            technique = 'SQL注入'
            recommendations = ['使用参数化查询', '部署WAF', '输入验证']

        # XSS特征
        elif any(kw in payload for kw in ['<script', 'javascript:', 'onerror=', 'alert(']):
            risk_score = 7.5
            technique = 'XSS跨站脚本'
            recommendations = ['输出编码', 'CSP策略', '输入过滤']

        # 命令注入特征
        elif any(kw in payload for kw in ['wget', 'curl', 'bash', '| ', '; ', '&& ']):
            risk_score = 9.0
            technique = '命令注入'
            recommendations = ['禁用危险函数', '白名单验证', '权限最小化']

        # C2通信特征
        elif any(kw in payload for kw in ['http://', 'https://', 'powershell', 'cmd.exe']):
            risk_score = 8.0
            technique = 'C2通信'
            recommendations = ['阻断可疑IP', '流量监控', '终端检测']

        return {
            'attack_technique': technique,
            'risk_score': risk_score,
            'threat_level': '高危' if risk_score >= 7 else '中危' if risk_score >= 4 else '低危',
            'recommendations': recommendations,
            'analysis': f'基于规则分析识别为{technique}，风险评分{risk_score}'
        }
