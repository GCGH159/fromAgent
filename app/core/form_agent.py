"""
带记忆功能的表单管理 Agent - 支持持续性对话
"""
from typing import Optional
from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from app.tools.form_tools import (
    load_schema,
    set_field_value,
    get_field_value,
    get_all_values,
    get_all_values_tree,
    get_field_info,
    list_all_fields,
    set_field_visibility,
    set_field_required,
    get_field_dependencies,
    get_affected_fields,
    set_log_level
)
from app.core.chat_history import get_session_history
from config import config
import uuid


class FormAgentWithMemory:
    """
    带记忆功能的表单智能体
    - 支持持续性对话（对话历史存储在内存中）
    - 具备动态表单管理的能力
    """
    
    def __init__(self, session_id: Optional[str] = None):
        """
        初始化 Agent
        
        Args:
            session_id: 会话 ID，如果为 None 则自动生成
        """
        self.session_id = session_id or str(uuid.uuid4())
        
        # 1. 定义工具集
        self.tools = [
            load_schema,
            set_field_value,
            get_field_value,
            get_all_values,
            get_all_values_tree,
            get_field_info,
            list_all_fields,
            set_field_visibility,
            set_field_required,
            get_field_dependencies,
            get_affected_fields,
            set_log_level
        ]
        
        # 2. 创建系统提示词
        system_prompt = """你是一个智能表单助手，基于 DynamicFormEngine 表单引擎工作。

你的核心能力：
1. **表单结构管理**：
   - 使用 `load_schema` 工具加载表单结构定义（JSON 格式）
   - 使用 `list_all_fields` 查看所有字段
   - 使用 `get_field_info` 获取字段的详细信息

2. **字段值操作**：
   - 使用 `set_field_value` 设置字段值（支持嵌套字段，如 "app.region"）
   - 使用 `get_field_value` 获取单个字段的值
   - 使用 `get_all_values` 获取所有可见字段的值（平铺格式）
   - 使用 `get_all_values_tree` 获取所有可见字段的值（嵌套树格式）

3. **字段属性控制**：
   - 使用 `set_field_visibility` 设置字段的可见性
   - 使用 `set_field_required` 设置字段是否必填
   - 使用 `set_log_level` 调整日志级别

4. **依赖关系分析**：
   - 使用 `get_field_dependencies` 获取字段的依赖字段
   - 使用 `get_affected_fields` 获取受指定字段影响的其他字段

5. **对话记忆**：
   - 你可以记住之前的对话内容
   - 在回答问题时，可以参考之前的对话上下文
   - 用户可能会提到"刚才说的"、"之前的"等，请根据对话历史理解

6. **智能理解**：
   - 当用户说"设置区域为杭州"时，理解并调用 `set_field_value("region", "cn-hangzhou")`
   - 当用户说"查看所有值"时，调用 `get_all_values` 或 `get_all_values_tree`
   - 当用户说"隐藏应用名称"时，调用 `set_field_visibility("app.name", "false")`

7. **表单规则**：
   - 表单引擎支持字段规则（if/elif/else 条件逻辑）
   - 设置字段值时会自动触发相关规则
   - 可以通过依赖关系了解字段间的联动关系

使用说明：
- 字段值可以是字符串、数字、布尔值等，系统会自动解析
- 支持嵌套字段，使用点号分隔（如 "app.region"）
- JSON 格式的表单结构定义应该包含 fields 数组

请用中文回答用户。操作成功后，简要反馈结果。如果查询不到信息，请如实告知。
"""
        
        # 3. 创建 Agent（按照 LangChain 官网范式）
        # 如果配置了自定义的 API Key 或 Base URL，则使用 ChatOpenAI
        if config.LLM_API_KEY or config.LLM_BASE_URL != "https://api.openai.com/v1":
            from langchain_openai import ChatOpenAI
            from pydantic import SecretStr
            llm = ChatOpenAI(
                model=config.LLM_MODEL,
                api_key=SecretStr(config.LLM_API_KEY) if config.LLM_API_KEY else None,
                base_url=config.LLM_BASE_URL,
                temperature=config.LLM_TEMPERATURE,
            )
            self.agent = create_agent(
                model=llm,
                tools=self.tools,
                system_prompt=system_prompt
            )
        else:
            # 使用默认配置（直接传递模型名称）
            self.agent = create_agent(
                model=config.LLM_MODEL,
                tools=self.tools,
                system_prompt=system_prompt
            )
        
        # 4. 获取会话历史管理器
        self.history = get_session_history(self.session_id)
        
    def chat(self, user_input: str) -> str:
        """
        与 Agent 对话（支持持续性对话）
        
        Args:
            user_input: 用户输入
            
        Returns:
            Agent 的回复
        """
        try:
            # 获取历史消息
            history_messages = self.history.get_recent_messages(limit=50)
            
            # 构建包含历史的输入
            all_messages = history_messages + [{"role": "user", "content": user_input}]
            inputs = {"messages": all_messages}
            
            # 运行 Agent
            final_state = self.agent.invoke(inputs)
            
            # 获取最后一条消息 (AIMessage)
            messages = final_state.get("messages", [])
            if messages:
                last_message = messages[-1]
                response_content = last_message.content
                
                # 保存对话历史
                from langchain_core.messages import HumanMessage, AIMessage
                self.history.add_message(HumanMessage(content=user_input))
                self.history.add_message(AIMessage(content=response_content))
                
                return response_content
            return "Agent 没有回应。"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return f"❌ Agent 运行出错: {e}\n详细信息:\n{error_details}"
    
    def get_session_id(self) -> str:
        """获取当前会话 ID"""
        return self.session_id
    
    def clear_history(self):
        """清空当前会话的对话历史"""
        self.history.clear()
    
    def get_message_count(self) -> int:
        """获取当前会话的消息数量"""
        return self.history.get_message_count()
    
    def get_session_info(self) -> dict:
        """
        获取会话信息
        
        Returns:
            dict: 会话信息
        """
        return {
            "session_id": self.session_id,
            "message_count": self.get_message_count(),
            "llm_model": config.LLM_MODEL,
            "llm_temperature": config.LLM_TEMPERATURE
        }


# 默认实例（无持久化会话）
form_agent_with_memory = FormAgentWithMemory()


# 便捷函数
def create_session(session_id: Optional[str] = None) -> FormAgentWithMemory:
    """
    创建一个新的带记忆的 Agent 会话
    
    Args:
        session_id: 可选的会话 ID
        
    Returns:
        FormAgentWithMemory 实例
    """
    return FormAgentWithMemory(session_id)
