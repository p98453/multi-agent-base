#!/usr/bin/env python3
"""
优化后的路由智能体（Optimized Router Agent）

本模块实现了多智能体系统中的核心路由组件。路由智能体负责：
1. 接收告警数据（alert_data），从中提取文本特征
2. 基于关键词匹配和正则表达式模式匹配，计算告警与各攻击类别的匹配分数
3. 根据分数选择最佳路由，将告警派发到对应的专家智能体进行深度分析

设计思路：
- 采用"关键词 + 正则"双层匹配策略，兼顾速度与准确性
- 关键词匹配侧重快速筛选，权重为 0.6；正则匹配侧重精准识别，权重为 0.4
- 当所有类别得分都很低时（< 0.5），自动降低置信度，表示路由结果不确定
- 支持三大攻击类别：web_attack、vulnerability_attack、illegal_connection
"""
import re
import time
from typing import Dict, Any, Tuple
from src.utils.structured_logger import get_logger

class OptimizedRouterAgent:
    """路由智能体 - 精简版
    
    职责：
    - 分析告警文本内容，判断其所属的攻击类别
    - 基于关键词和正则表达式的双重评分机制进行路由决策
    - 返回路由结果（目标专家类型 + 置信度 + 耗时）
    """
    
    def __init__(self):
        """初始化路由智能体
        
        构建路由规则表，包含三大类攻击的关键词列表和正则表达式模式：
        - web_attack: Web应用层攻击（SQL注入、XSS、目录遍历等）
        - vulnerability_attack: 漏洞利用攻击（CVE、Exploit、Shellcode等）
        - illegal_connection: 非法连接/网络攻击（C2通信、僵尸网络、DDoS等）
        
        初始化完成后，所有正则表达式会被预编译（compiled_patterns），
        避免每次路由时重复编译，提升匹配效率。
        """
        # 路由规则字典：每个攻击类别包含 keywords（关键词列表）和 patterns（正则模式列表）
        self.routing_rules = {
            'web_attack': {
                # Web攻击相关关键词，用于快速文本匹配
                'keywords': ['sql', 'xss', 'script', 'inject', 'union', 'select', 
                           'webshell', 'upload', 'traversal'],
                # Web攻击相关正则表达式，用于精准模式匹配
                'patterns': [
                    r'(?i)(union\s+select|select\s+.*\s+from)',   # SQL注入典型模式：UNION SELECT 或 SELECT ... FROM
                    r'(?i)(<script|javascript:|on\w+=)',           # XSS攻击模式：<script>标签、javascript:协议、事件处理器
                    r'(?i)(\.\.\/|\.\.\\|%2e%2e)',                 # 目录遍历模式：../、..\、URL编码的 %2e%2e
                ]
            },
            'vulnerability_attack': {
                # 漏洞利用相关关键词
                'keywords': ['cve', 'exploit', 'vulnerability', 'payload', 
                           'shellcode', 'overflow', '0day'],
                # 漏洞利用相关正则表达式
                'patterns': [
                    r'(?i)(cve-\d{4}-\d+)',           # CVE漏洞编号模式：CVE-年份-编号
                    r'(?i)(exploit|vulnerability)',    # 漏洞利用关键词匹配
                    r'(?i)(shellcode|payload)',        # Shellcode/载荷关键词匹配
                ]
            },
            'illegal_connection': {
                # 非法连接/网络攻击相关关键词
                'keywords': ['c2', 'command and control', 'tor', 'proxy', 
                           'tunnel', 'botnet', 'ddos'],
                # 非法连接相关正则表达式
                'patterns': [
                    r'(?i)(c2\s+communication)',    # C2（Command & Control）通信模式
                    r'(?i)(botnet|zombie)',          # 僵尸网络关键词
                    r'(?i)(ddos|dos\s+attack)',      # DDoS/DoS攻击模式
                ]
            }
        }
        
        # 预编译所有正则表达式模式
        # 将字符串形式的正则预编译为 re.Pattern 对象，后续匹配时直接使用 pattern.search()
        # 好处：避免每次路由决策时都重新编译正则，显著提升性能
        for category in self.routing_rules:
            patterns = self.routing_rules[category]['patterns']
            self.routing_rules[category]['compiled_patterns'] = [
                re.compile(pattern) for pattern in patterns
            ]
        
        # 获取全局结构化日志记录器，用于记录路由决策过程
        self.logger = get_logger()
    
    async def route(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """路由决策（异步方法）
        
        这是路由智能体的核心入口方法，执行完整的路由决策流程：
        1. 从告警数据中提取并合并文本特征（attack_type + payload + raw_log）
        2. 调用 _calculate_scores() 计算各攻击类别的匹配分数
        3. 调用 _select_route() 选择得分最高的类别作为路由目标
        4. 记录决策日志并返回路由结果
        
        Args:
            alert_data: 告警数据字典，至少包含以下已知字段：
                - attack_type (str): 攻击类型描述
                - payload (str): 攻击载荷内容
                - raw_log (str): 原始日志文本（可选）
                
        Returns:
            dict: 路由决策结果，包含：
                - selected_route (str): 选择的专家类型（如 'web_attack'）
                - confidence (float): 路由置信度（0~1）
                - processing_time_ms (int): 路由决策耗时（毫秒）
        """
        start_time = time.time()
        
        # 提取告警数据中的关键文本字段
        # 将 attack_type、payload、raw_log 三个字段拼接为一个文本，统一转小写以实现大小写无关匹配
        attack_type = alert_data.get('attack_type', '')
        payload = alert_data.get('payload', '')
        raw_log = alert_data.get('raw_log', '')
        combined_text = f"{attack_type} {payload} {raw_log}".lower()
        
        # 计算当前告警文本与各攻击类别的匹配分数
        route_scores = self._calculate_scores(combined_text)
        
        # 根据匹配分数选择最佳路由和对应的置信度
        selected_route, confidence = self._select_route(route_scores)
        
        # 计算路由决策耗时（毫秒）
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # 记录路由决策日志，包含用户查询、路由结果、置信度、耗时和各类别得分
        self.logger.log("router_decision", {
            "user_query": alert_data.get('attack_type', '')[:100],             # 截取前100字符防止日志过长
            "selected_route": selected_route,                                   # 最终选择的路由目标
            "confidence": round(confidence, 3),                                 # 置信度保留3位小数
            "processing_time_ms": processing_time_ms,                           # 决策耗时
            "route_scores": {k: round(v, 2) for k, v in route_scores.items() if k in ['web_attack', 'vulnerability_attack', 'illegal_connection']}  # 各类别得分
        })
        
        return {
            'selected_route': selected_route,
            'confidence': confidence,
            'processing_time_ms': processing_time_ms
        }
    
    def _calculate_scores(self, text: str) -> Dict[str, float]:
        """计算各攻击类别的匹配分数
        
        对每个攻击类别，分别进行关键词匹配和正则匹配，加权求和得到综合得分。
        
        评分规则：
        - 关键词匹配：统计该类别下关键词在文本中出现的个数，每命中一个关键词加 0.6 分
        - 正则匹配：统计该类别下编译后的正则表达式在文本中匹配成功的个数，每命中一个模式加 0.4 分
        - 总分 = 关键词命中数 × 0.6 + 正则命中数 × 0.4
        
        Args:
            text: 预处理后的小写文本（由 attack_type + payload + raw_log 拼接而成）
            
        Returns:
            dict: 类别名 -> 匹配分数 的映射，如 {'web_attack': 1.8, 'vulnerability_attack': 0.0, ...}
        """
        scores = {}
        
        for category, rules in self.routing_rules.items():
            score = 0.0
            
            # 关键词匹配：遍历该类别的所有关键词，统计在文本中出现的数量
            # 使用简单的 `in` 操作符判断子串存在性，速度快
            keyword_matches = sum(1 for kw in rules['keywords'] if kw in text)
            score += keyword_matches * 0.6  # 关键词匹配权重为 0.6
            
            # 正则匹配：使用预编译的正则表达式进行模式搜索
            # 相比关键词匹配，正则可以识别更复杂的攻击模式（如 UNION SELECT 中间有空格等）
            pattern_matches = sum(1 for pattern in rules['compiled_patterns'] if pattern.search(text))
            score += pattern_matches * 0.4  # 正则匹配权重为 0.4
            
            scores[category] = score
        
        return scores
    
    def _select_route(self, scores: Dict[str, float]) -> Tuple[str, float]:
        """根据匹配分数选择最佳路由
        
        在三大攻击类别中，选择得分最高的作为路由目标。
        同时根据最高得分计算置信度：
        - 若最高得分 < 0.5，表示没有类别有明显匹配，置信度固定为 0.3（低置信度）
        - 若最高得分 >= 0.5，置信度 = best_score / 3.0，上限为 1.0
          （即满分约为 3.0 分时置信度达到 100%）
        - 当所有类别得分都为 0 时，默认路由到 web_attack 专家
        
        Args:
            scores: 各攻击类别的匹配分数字典
            
        Returns:
            tuple: (最佳路由类别名, 置信度)
        """
        # 仅在三个主要攻击类别中选择路由目标
        main_categories = ['web_attack', 'vulnerability_attack', 'illegal_connection']
        
        best_route = 'web_attack'  # 默认路由目标：当所有得分都为0时，回退到 web_attack
        best_score = 0.0
        
        # 遍历各类别，找出得分最高的类别
        for category in main_categories:
            score = scores.get(category, 0.0)
            if score > best_score:
                best_score = score
                best_route = category
        
        # 根据最高得分计算置信度
        # 如果最高分过低（< 0.5），说明告警文本不明确，设置低置信度 0.3
        if best_score < 0.5:
            confidence = 0.3
        else:
            # 将得分映射到 [0, 1] 区间：得分 3.0 对应置信度 1.0
            confidence = min(best_score / 3.0, 1.0)
        
        return best_route, confidence
