"""
对话历史管理模块
支持基于内存的对话历史存储和检索
"""
from typing import List, Optional
from datetime import datetime
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
import json


class ChatHistory:
    """
    对话历史管理类
    支持消息的存储、检索和清理
    """
    
    def __init__(self, session_id: str, max_messages: int = 50):
        """
        初始化对话历史
        
        Args:
            session_id: 会话 ID
            max_messages: 最大消息数量
        """
        self.session_id = session_id
        self.max_messages = max_messages
        self.messages: List[BaseMessage] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
    
    def add_message(self, message: BaseMessage):
        """
        添加消息到历史记录
        
        Args:
            message: 消息对象（HumanMessage, AIMessage, SystemMessage）
        """
        self.messages.append(message)
        self.updated_at = datetime.now()
        
        # 限制消息数量
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
    
    def get_recent_messages(self, limit: Optional[int] = None) -> List[dict]:
        """
        获取最近的消息
        
        Args:
            limit: 返回消息数量限制，None 表示返回全部
            
        Returns:
            List[dict]: 消息列表，每个消息包含 role 和 content
        """
        if limit is None:
            limit = len(self.messages)
        else:
            limit = min(limit, len(self.messages))
        
        recent_messages = self.messages[-limit:]
        
        # 转换为字典格式
        result = []
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                result.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                result.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                result.append({"role": "system", "content": msg.content})
        
        return result
    
    def get_message_count(self) -> int:
        """
        获取当前消息数量
        
        Returns:
            int: 消息数量
        """
        return len(self.messages)
    
    def clear(self):
        """清空所有消息"""
        self.messages.clear()
        self.updated_at = datetime.now()
    
    def get_session_id(self) -> str:
        """
        获取会话 ID
        
        Returns:
            str: 会话 ID
        """
        return self.session_id
    
    def to_dict(self) -> dict:
        """
        将对话历史转换为字典
        
        Returns:
            dict: 对话历史的字典表示
        """
        return {
            "session_id": self.session_id,
            "messages": [
                {
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant" if isinstance(msg, AIMessage) else "system",
                    "content": msg.content
                }
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "message_count": len(self.messages)
        }
    
    def from_dict(self, data: dict):
        """
        从字典加载对话历史
        
        Args:
            data: 对话历史的字典表示
        """
        self.session_id = data.get("session_id", self.session_id)
        self.messages.clear()
        
        for msg_data in data.get("messages", []):
            role = msg_data.get("role")
            content = msg_data.get("content")
            
            if role == "user":
                self.messages.append(HumanMessage(content=content))
            elif role == "assistant":
                self.messages.append(AIMessage(content=content))
            elif role == "system":
                self.messages.append(SystemMessage(content=content))
        
        self.updated_at = datetime.now()


# 全局会话存储（内存存储）
_sessions: dict = {}


def get_session_history(session_id: str) -> ChatHistory:
    """
    获取或创建会话历史
    
    Args:
        session_id: 会话 ID
        
    Returns:
        ChatHistory: 对话历史对象
    """
    if session_id not in _sessions:
        from config import config
        _sessions[session_id] = ChatHistory(
            session_id=session_id,
            max_messages=config.SESSION_MAX_MESSAGES
        )
    
    return _sessions[session_id]


def delete_session(session_id: str) -> bool:
    """
    删除会话
    
    Args:
        session_id: 会话 ID
        
    Returns:
        bool: 是否删除成功
    """
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def list_sessions() -> List[dict]:
    """
    列出所有会话
    
    Returns:
        List[dict]: 会话列表
    """
    return [
        {
            "session_id": session_id,
            "message_count": history.get_message_count(),
            "created_at": history.created_at.isoformat(),
            "updated_at": history.updated_at.isoformat()
        }
        for session_id, history in _sessions.items()
    ]


def clear_all_sessions():
    """清空所有会话"""
    _sessions.clear()


# 导出
__all__ = [
    "ChatHistory",
    "get_session_history",
    "delete_session",
    "list_sessions",
    "clear_all_sessions"
]
