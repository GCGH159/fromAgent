"""
FormAgent LangChain 工具函数
将 DynamicFormEngine 的功能封装为 LangChain 可调用的工具
"""
from typing import Any, Dict, Optional, List
from langchain_core.tools import tool
from agentFrom import DynamicFormEngine
import json


# 全局表单引擎实例（单例模式）
_form_engine: Optional[DynamicFormEngine] = None


def get_form_engine() -> DynamicFormEngine:
    """
    获取表单引擎实例（单例）
    
    Returns:
        DynamicFormEngine: 表单引擎实例
    """
    global _form_engine
    if _form_engine is None:
        # 初始化默认表单引擎
        _form_engine = DynamicFormEngine(
            schema={"fields": []},
            log_level=2
        )
    return _form_engine


def set_form_engine(engine: DynamicFormEngine):
    """
    设置表单引擎实例
    
    Args:
        engine: 表单引擎实例
    """
    global _form_engine
    _form_engine = engine


@tool
def load_schema(schema: str) -> str:
    """
    加载表单结构定义
    
    Args:
        schema: JSON 格式的表单结构定义字符串
        
    Returns:
        str: 操作结果消息
        
    Example:
        schema = '{"fields": [{"key": "name", "name": "姓名", "type": "text"}]}'
        load_schema(schema)
    """
    try:
        schema_dict = json.loads(schema)
        engine = get_form_engine()
        
        # 重新创建表单引擎
        global _form_engine
        _form_engine = DynamicFormEngine(
            schema=schema_dict,
            log_level=2
        )
        
        return f"✅ 表单结构加载成功，共 {len(_form_engine.fields)} 个字段"
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败: {e}"
    except Exception as e:
        return f"❌ 加载表单结构失败: {e}"


@tool
def set_field_value(key: str, value: str) -> str:
    """
    设置字段值
    
    Args:
        key: 字段键名（支持嵌套，如 "app.region"）
        value: 字段值（字符串格式，会自动转换为合适的类型）
        
    Returns:
        str: 操作结果消息
        
    Example:
        set_field_value("region", "cn-hangzhou")
        set_field_value("count", "10")
    """
    try:
        engine = get_form_engine()
        
        # 尝试解析值类型
        parsed_value = _parse_value(value)
        
        # 设置字段值
        engine.set_value(key, parsed_value)
        
        return f"✅ 字段 {key} 的值已设置为: {parsed_value}"
    except Exception as e:
        return f"❌ 设置字段值失败: {e}"


@tool
def get_field_value(key: str) -> str:
    """
    获取字段值
    
    Args:
        key: 字段键名（支持嵌套，如 "app.region"）
        
    Returns:
        str: 字段值的 JSON 字符串表示
        
    Example:
        get_field_value("region")
    """
    try:
        engine = get_form_engine()
        value = engine.get_value(key)
        
        # 转换为 JSON 字符串
        result = json.dumps(value, ensure_ascii=False, indent=2)
        return f"✅ 字段 {key} 的值: {result}"
    except Exception as e:
        return f"❌ 获取字段值失败: {e}"


@tool
def get_all_values() -> str:
    """
    获取所有可见字段的值（平铺格式）
    
    Returns:
        str: 所有字段值的 JSON 字符串表示
        
    Example:
        get_all_values()
    """
    try:
        engine = get_form_engine()
        values = engine.get_visible_values()
        
        result = json.dumps(values, ensure_ascii=False, indent=2)
        return f"✅ 所有可见字段的值:\n{result}"
    except Exception as e:
        return f"❌ 获取字段值失败: {e}"


@tool
def get_all_values_tree() -> str:
    """
    获取所有可见字段的值（嵌套树格式）
    
    Returns:
        str: 所有字段值的嵌套 JSON 字符串表示
        
    Example:
        get_all_values_tree()
    """
    try:
        engine = get_form_engine()
        values = engine.get_visible_values_tree()
        
        result = json.dumps(values, ensure_ascii=False, indent=2)
        return f"✅ 所有可见字段的值（树格式）:\n{result}"
    except Exception as e:
        return f"❌ 获取字段值失败: {e}"


@tool
def get_field_info(key: str) -> str:
    """
    获取字段的详细信息
    
    Args:
        key: 字段键名
        
    Returns:
        str: 字段信息的 JSON 字符串表示
        
    Example:
        get_field_info("region")
    """
    try:
        engine = get_form_engine()
        
        if key not in engine.fields:
            return f"❌ 字段 {key} 不存在"
        
        field = engine.fields[key]
        field_info = {
            "key": field.key,
            "name": field.name,
            "type": field.type,
            "value": field.value,
            "visible": field.visible,
            "disabled": field.disabled,
            "required": field.required,
            "dependencies": field.dependencies,
            "options": field.options,
            "errors": field.errors
        }
        
        result = json.dumps(field_info, ensure_ascii=False, indent=2)
        return f"✅ 字段 {key} 的信息:\n{result}"
    except Exception as e:
        return f"❌ 获取字段信息失败: {e}"


@tool
def list_all_fields() -> str:
    """
    列出所有字段
    
    Returns:
        str: 所有字段列表的 JSON 字符串表示
        
    Example:
        list_all_fields()
    """
    try:
        engine = get_form_engine()
        fields_list = []
        
        for key, field in engine.fields.items():
            field_info = {
                "key": field.key,
                "name": field.name,
                "type": field.type,
                "visible": field.visible,
                "required": field.required
            }
            fields_list.append(field_info)
        
        result = json.dumps(fields_list, ensure_ascii=False, indent=2)
        return f"✅ 所有字段列表:\n{result}"
    except Exception as e:
        return f"❌ 列出字段失败: {e}"


@tool
def set_field_visibility(key: str, visible: str) -> str:
    """
    设置字段的可见性
    
    Args:
        key: 字段键名
        visible: 可见性（"true" 或 "false"）
        
    Returns:
        str: 操作结果消息
        
    Example:
        set_field_visibility("app.name", "true")
    """
    try:
        engine = get_form_engine()
        
        if key not in engine.fields:
            return f"❌ 字段 {key} 不存在"
        
        visible_bool = visible.lower() in ("true", "1", "yes")
        engine.fields[key].visible = visible_bool
        
        status = "可见" if visible_bool else "隐藏"
        return f"✅ 字段 {key} 已设置为{status}"
    except Exception as e:
        return f"❌ 设置字段可见性失败: {e}"


@tool
def set_field_required(key: str, required: str) -> str:
    """
    设置字段是否必填
    
    Args:
        key: 字段键名
        required: 是否必填（"true" 或 "false"）
        
    Returns:
        str: 操作结果消息
        
    Example:
        set_field_required("app.name", "true")
    """
    try:
        engine = get_form_engine()
        
        if key not in engine.fields:
            return f"❌ 字段 {key} 不存在"
        
        required_bool = required.lower() in ("true", "1", "yes")
        engine.fields[key].required = required_bool
        
        status = "必填" if required_bool else "非必填"
        return f"✅ 字段 {key} 已设置为{status}"
    except Exception as e:
        return f"❌ 设置字段必填状态失败: {e}"


@tool
def get_field_dependencies(key: str) -> str:
    """
    获取字段的依赖关系
    
    Args:
        key: 字段键名
        
    Returns:
        str: 依赖关系的 JSON 字符串表示
        
    Example:
        get_field_dependencies("app.name")
    """
    try:
        engine = get_form_engine()
        
        if key not in engine.fields:
            return f"❌ 字段 {key} 不存在"
        
        field = engine.fields[key]
        dependencies = field.dependencies
        
        result = json.dumps(dependencies, ensure_ascii=False, indent=2)
        return f"✅ 字段 {key} 的依赖字段:\n{result}"
    except Exception as e:
        return f"❌ 获取字段依赖关系失败: {e}"


@tool
def get_affected_fields(key: str) -> str:
    """
    获取受指定字段影响的其他字段
    
    Args:
        key: 字段键名
        
    Returns:
        str: 受影响字段列表的 JSON 字符串表示
        
    Example:
        get_affected_fields("region")
    """
    try:
        engine = get_form_engine()
        
        if key not in engine.fields:
            return f"❌ 字段 {key} 不存在"
        
        affected = engine._get_affected_fields(key)
        
        result = json.dumps(affected, ensure_ascii=False, indent=2)
        return f"✅ 受字段 {key} 影响的字段:\n{result}"
    except Exception as e:
        return f"❌ 获取受影响字段失败: {e}"


@tool
def set_log_level(level: str) -> str:
    """
    设置表单引擎的日志级别
    
    Args:
        level: 日志级别（"0"=无输出, "1"=错误, "2"=警告+错误, "3"=调试+警告+错误）
        
    Returns:
        str: 操作结果消息
        
    Example:
        set_log_level("3")
    """
    try:
        engine = get_form_engine()
        level_int = int(level)
        
        engine.set_log_level(level_int)
        
        level_names = {
            0: "无输出",
            1: "仅错误",
            2: "警告 + 错误",
            3: "调试 + 警告 + 错误"
        }
        
        return f"✅ 日志级别已设置为: {level_names.get(level_int, level)}"
    except Exception as e:
        return f"❌ 设置日志级别失败: {e}"


def _parse_value(value: str) -> Any:
    """
    解析字符串值为合适的类型
    
    Args:
        value: 字符串值
        
    Returns:
        Any: 解析后的值（可能是 int, float, bool, str 等）
    """
    value = value.strip()
    
    # 尝试解析为布尔值
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    
    # 尝试解析为 None
    if value.lower() in ("null", "none"):
        return None
    
    # 尝试解析为整数
    try:
        return int(value)
    except ValueError:
        pass
    
    # 尝试解析为浮点数
    try:
        return float(value)
    except ValueError:
        pass
    
    # 尝试解析为 JSON（列表或字典）
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        pass
    
    # 默认返回字符串
    return value


# 导出所有工具
__all__ = [
    "load_schema",
    "set_field_value",
    "get_field_value",
    "get_all_values",
    "get_all_values_tree",
    "get_field_info",
    "list_all_fields",
    "set_field_visibility",
    "set_field_required",
    "get_field_dependencies",
    "get_affected_fields",
    "set_log_level",
    "get_form_engine",
    "set_form_engine"
]
