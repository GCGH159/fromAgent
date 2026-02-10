"""
FormAgent 配置文件
支持从环境变量或 .env 文件读取配置
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Config(BaseSettings):
    """
    应用配置类
    使用 Pydantic Settings 进行配置管理
    """
    
    # LLM 配置
    LLM_MODEL: str = "gpt-4o-mini"  # 默认使用 GPT-4o-mini
    LLM_API_KEY: Optional[str] = None  # OpenAI API Key
    LLM_BASE_URL: str = "https://api.openai.com/v1"  # API 基础 URL
    LLM_TEMPERATURE: float = 0.7  # 温度参数
    
    # 表单引擎配置
    FORM_KEY_SEP: str = "."  # 嵌套字段分隔符
    FORM_LOG_LEVEL: int = 2  # 日志级别（0=无输出, 1=错误, 2=警告+错误, 3=调试+警告+错误）
    
    # 会话配置
    SESSION_MAX_MESSAGES: int = 50  # 会话最大消息数
    SESSION_TIMEOUT: int = 3600  # 会话超时时间（秒）
    
    # 调试配置
    DEBUG: bool = False  # 调试模式
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 创建全局配置实例
config = Config()
