#!/usr/bin/env python3
"""
结构化日志记录模块（Structured Logger）

本模块提供 JSON 格式的结构化日志系统，用于追踪多智能体系统的完整处理链路。

核心功能：
1. 实时日志写入：每条日志立即追加到本地 JSONL 文件，确保异常退出时不丢失数据
2. 内存日志副本：在内存中保留所有日志条目，支持快速查询和统计
3. 性能统计：自动统计总 token 消耗、总处理时间、各阶段调用次数和耗时
4. 会话摘要：支持生成完整的会话统计摘要文件

日志文件格式：
- 主日志文件：analysis_YYYYMMDD_HHMMSS.jsonl（JSONL 格式，每行一条 JSON 记录）
- 摘要文件：analysis_YYYYMMDD_HHMMSS.summary.json（JSON 格式，包含统计信息）

日志事件类型（stage）：
- session_start: 日志会话开始
- user_input: 用户提交的告警数据
- router_decision: 路由智能体的决策结果
- llm_inference: LLM 调用性能数据
- llm_inference_error: LLM 调用失败记录
- expert_analysis: 专家分析完成记录
- final_result: 最终分析结果
- session_end: 日志会话结束
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class StructuredLogger:
    """结构化日志记录器 - 实时写入本地文件
    
    每次创建新实例（即新的分析会话）时，会自动创建一个以时间戳命名的日志文件。
    所有日志条目同时保存在内存（log_entries 列表）和磁盘（JSONL 文件）中。
    """
    
    def __init__(self, log_dir: str = "logs"):
        """初始化日志记录器
        
        Args:
            log_dir: 日志文件存储目录（默认为项目根目录下的 "logs" 文件夹）
        """
        # 创建日志目录（如果不存在）
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)       # exist_ok=True: 目录已存在时不报错
        
        # 生成日志文件路径：logs/analysis_YYYYMMDD_HHMMSS.jsonl
        # 使用精确到秒的时间戳确保每次会话的日志文件唯一
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"analysis_{timestamp}.jsonl"
        
        # 内存中的日志条目列表，保存所有日志的副本
        # 用途：快速统计查询，不需要从磁盘读取
        self.log_entries = []
        
        # 累积统计信息字典
        self.stats = {
            "total_tokens": 0,      # 累积消耗的 token 总数（输入 + 输出）
            "total_time_ms": 0,     # 累积处理时间（毫秒）
            "stages": {}            # 各阶段的统计：{stage_name: {count, total_time_ms}}
        }

        # 写入会话开始标记，标志一个新的分析会话
        self._append_to_file({
            "event": "session_start",
            "timestamp": datetime.now().isoformat(),
            "log_file": str(self.log_file)
        })
    
    def log(self, stage: str, data: Dict[str, Any], level: str = "INFO"):
        """记录一条结构化日志，同时写入内存和磁盘
        
        每条日志包含：时间戳、日志级别、阶段名称、以及阶段特定的数据字段。
        
        Args:
            stage: 日志阶段名称，标识这条日志属于哪个处理环节
                   如 "router_decision", "llm_inference", "expert_analysis" 等
            data: 阶段特定的数据字典，包含该阶段需要记录的详细信息
                  常用字段：processing_time_ms, input_tokens, output_tokens 等
            level: 日志级别（默认 "INFO"），可选 "ERROR", "WARN" 等
        """
        # 构建日志条目：时间戳 + 级别 + 阶段 + 阶段数据
        # 使用 **data 展开操作符将阶段数据平铺到日志条目中
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "stage": stage,
            **data                  # 将 data 字典中的所有键值对展开到 entry 中
        }
        
        # 同时保存到内存列表
        self.log_entries.append(entry)
        
        # ===== 实时追加写入本地 JSONL 文件 =====
        # 每条日志立即写入磁盘，确保即使程序异常终止也不会丢失日志
        self._append_to_file(entry)
        
        # ===== 更新累积统计信息 =====
        
        # 累加处理时间
        if "processing_time_ms" in data:
            self.stats["total_time_ms"] += data["processing_time_ms"]
        
        # 累加 token 消耗量（分别统计输入和输出 token）
        if "input_tokens" in data:
            self.stats["total_tokens"] += data.get("input_tokens", 0)
        if "output_tokens" in data:
            self.stats["total_tokens"] += data.get("output_tokens", 0)
            
        # 按阶段分组统计：记录每个阶段的调用次数和累积耗时
        if stage not in self.stats["stages"]:
            self.stats["stages"][stage] = {"count": 0, "total_time_ms": 0}
        self.stats["stages"][stage]["count"] += 1
        if "processing_time_ms" in data:
            self.stats["stages"][stage]["total_time_ms"] += data["processing_time_ms"]
        
        # 控制台实时输出日志（方便开发调试）
        # ensure_ascii=False 确保中文字符正常显示
        print(f"[{level}] {stage}: {json.dumps(data, ensure_ascii=False)}")
    
    def _append_to_file(self, entry: Dict[str, Any]):
        """追加一条 JSON 行到日志文件（JSONL 格式）
        
        JSONL（JSON Lines）格式：每行一个独立的 JSON 对象，便于逐行读取和流式处理。
        使用 "a"（append）模式打开文件，确保新日志追加到文件末尾。
        
        Args:
            entry: 要写入的日志条目字典
        """
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            # 日志写入失败不应影响主业务流程，仅打印警告
            print(f"[WARN] 日志写入失败: {e}")
    
    def save(self):
        """保存完整的会话摘要到独立文件
        
        在分析完成后调用，生成一个 .summary.json 文件，
        包含会话起止时间、日志条数和累积统计信息。
        同时在主日志文件中写入 session_end 事件标记。
        
        Returns:
            str: 主日志文件的路径
        """
        # 生成摘要文件路径：将 .jsonl 后缀替换为 .summary.json
        summary_file = self.log_file.with_suffix(".summary.json")
        
        # 构建会话摘要
        output = {
            "session_start": self.log_entries[0]["timestamp"] if self.log_entries else None,
            "session_end": datetime.now().isoformat(),
            "total_entries": len(self.log_entries),     # 本次会话的日志总条数
            "statistics": self.stats,                   # 累积统计信息
            "log_file": str(self.log_file)              # 主日志文件路径
        }
        
        # 写入摘要文件（格式化 JSON，便于人工阅读）
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        # 在主日志文件中写入会话结束标记
        self._append_to_file({
            "event": "session_end",
            "timestamp": datetime.now().isoformat(),
            "total_entries": len(self.log_entries),
            "statistics": self.stats
        })
        
        print(f"\n日志已保存到: {self.log_file}")
        print(f"会话摘要: {summary_file}")
        return str(self.log_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取当前会话的累积统计信息
        
        返回统计信息的副本（深拷贝），防止外部修改影响内部状态。
        
        Returns:
            dict: 统计信息字典，包含 total_tokens, total_time_ms, stages 等
        """
        return self.stats.copy()


# ==================== 全局日志实例管理 ====================
# 使用模块级全局变量实现日志记录器的单例模式
_global_logger: Optional[StructuredLogger] = None

def get_logger() -> StructuredLogger:
    """获取全局日志记录器实例（惰性初始化）
    
    首次调用时创建 StructuredLogger 实例，后续调用返回同一实例。
    确保整个应用共享同一个日志记录器和日志文件。
    
    Returns:
        StructuredLogger: 全局唯一的日志记录器实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger()
    return _global_logger

def reset_logger():
    """重置全局日志记录器（用于新的分析会话）
    
    创建一个全新的 StructuredLogger 实例（新的日志文件和统计数据），
    替换之前的全局实例。通常在 MultiAgentSystem.initialize() 中调用。
    
    Returns:
        StructuredLogger: 新创建的全局日志记录器实例
    """
    global _global_logger
    _global_logger = StructuredLogger()
    return _global_logger
