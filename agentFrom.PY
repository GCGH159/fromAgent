from typing import Dict, Any, List, Optional, Callable, Union
from collections import deque
import re
import traceback
import logging


# ============= 日志控制 =============
class FormEngineLogger:
    """
    表单引擎日志控制类
    支持多种日志级别控制
    """
    def __init__(self, max_content_size: int = 1024*30):  # 10KB default
        # 日志级别：0=无输出, 1=错误, 2=警告+错误, 3=调试+警告+错误
        self.log_level = 2  # 默认只显示警告和错误
        self.debug_enabled = False  # 详细调试模式
        self.verbose_enabled = False  # 详细输出模式
        self.max_content_size = max_content_size  # 最大内容大小限制（字节）

    def set_log_level(self, level: int):
        """
        设置日志级别
        0: 无输出
        1: 仅错误
        2: 警告 + 错误 (默认)
        3: 调试 + 警告 + 错误
        """
        self.log_level = level
        self.debug_enabled = level >= 3
        self.verbose_enabled = level >= 3

    def should_log(self, level: str) -> bool:
        """判断是否应该输出日志"""
        if self.log_level == 0:
            return False
        if level == "error":
            return self.log_level >= 1
        elif level == "warning":
            return self.log_level >= 2
        elif level == "debug":
            return self.log_level >= 3
        return False

    def _should_print_content(self, content: str) -> bool:
        """检查内容大小是否在限制范围内"""
        if not content:
            return True
        # 计算字符串的字节大小
        content_size = len(content.encode('utf-8'))
        return content_size <= self.max_content_size

    def error(self, msg: str):
        """错误日志"""
        if self.should_log("error") and self._should_print_content(msg):
            print(f"[错误] {msg}")
        elif self.should_log("error"):
            print(f"[错误] 内容过大，已跳过打印 (内容长度: {len(msg.encode('utf-8'))} 字节)")

    def warning(self, msg: str):
        """警告日志"""
        if self.should_log("warning") and self._should_print_content(msg):
            print(f"[警告] {msg}")
        elif self.should_log("warning"):
            print(f"[警告] 内容过大，已跳过打印 (内容长度: {len(msg.encode('utf-8'))} 字节)")

    def debug(self, msg: str):
        """调试日志"""
        if self.should_log("debug") and self._should_print_content(msg):
            print(f"[调试] {msg}")
        elif self.should_log("debug"):
            print(f"[调试] 内容过大，已跳过打印 (内容长度: {len(msg.encode('utf-8'))} 字节)")

    def verbose(self, msg: str):
        """详细输出日志（用于非常详细的信息）"""
        if self.verbose_enabled and self._should_print_content(msg):
            print(f"[详细] {msg}")
        elif self.verbose_enabled:
            print(f"[详细] 内容过大，已跳过打印 (内容长度: {len(msg.encode('utf-8'))} 字节)")

    def set_max_content_size(self, size: int):
        """设置最大内容大小限制（字节）"""
        self.max_content_size = size

# 创建全局日志实例
logger = FormEngineLogger()  # 使用默认的10KB限制


# ============= 驼峰式参数支持工具函数 =============




class Field:
    def __init__(self, data: dict):
        # 字段唯一标识（全表单唯一，规则/依赖/取值都通过它引用）
        self.key: str = data["key"]
        # 字段展示名（给 UI 用的 label/title）
        self.name: str = data["name"]
        # 字段类型
        self.type: str = data["type"]

        # 数据源标识（可选）：声明 options/value 可能来自哪个数据源
        self.data_source: Optional[str] = data.get("data_source")
        # 候选项（可选）：select/radio 等使用，结构通常为 [{"label":..,"value":..}, ...]
        self.options: Optional[List[dict]] = data.get("options")
        # 当前值：用户输入/选择或规则计算回填的值
        self.value: Any = data.get("value")

        # 依赖字段 key 列表：这些字段变化时，本字段需要重新跑 rules
        self.dependencies: List[str] = data.get("dependencies", [])
        # 规则列表：if/then/elif/else 等（内部配置的 DSL）
        self.rules: List[dict] = data.get("rules", [])
        # 描述信息
        self.description: str = data.get("description", "")
        # UI/校验状态
        self.visible: bool = data.get("visible", True)      # 是否可见
        self.disabled: bool = data.get("disabled", False)   # 是否禁用
        self.required: bool = data.get("required", False)   # 是否必填
        self.errors: str = data.get("errors", "")           # 错误信息（改为字符串）

        self.render: bool = data.get("render", True) # ⭐ 是否渲染（submit/can_submit 用 False）


class _AttrDict(dict):
    """支持点访问：d.a 等价 d['a']"""
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)


class _FieldView:
    """
    暴露给规则表达式用的字段视图（只读语义）。
    让 if 表达式里可以写：f.regression.options / f.region.value 等。
    """
    __slots__ = ("key", "value", "options", "visible", "disabled", "required", "errors")

    def __init__(self, field: Field):
        self.key = field.key
        self.value = field.value
        self.options = field.options
        self.visible = field.visible
        self.disabled = field.disabled
        self.required = field.required
        self.errors = field.errors


def _set_nested(d: dict, path: List[str], value: Any):
    cur = d
    for p in path[:-1]:
        if p not in cur or not isinstance(cur[p], dict):
            cur[p] = {}
        cur = cur[p]
    cur[path[-1]] = value


def _get_nested(d: dict, path: List[str], default=None):
    cur = d
    for p in path:
        if not isinstance(cur, dict) or p not in cur:
            return default
        cur = cur[p]
    return cur


def _build_attr_tree(items: Dict[str, Any], sep: str = ".") -> _AttrDict:
    """
    把 {"a.b": 1, "a.c": 2, "x": 3} 变成可点访问树：
    tree.a.b == 1, tree.a.c == 2, tree.x == 3
    """
    root = {}
    for k, v in items.items():
        parts = k.split(sep)
        _set_nested(root, parts, v)

    def wrap(obj):
        if isinstance(obj, dict):
            return _AttrDict({kk: wrap(vv) for kk, vv in obj.items()})
        elif isinstance(obj, list):
            return [wrap(vv) for vv in obj]
        return obj

    return wrap(root)


class DynamicFormEngine:
    def __init__(self, schema: Any, key_sep: str = ".", log_level: int = 3):
        self.key_sep = key_sep
        self.fields: Dict[str, Field] = {}
        self.values: Dict[str, Any] = {}
        self.temp_vars: Dict[str, Any] = {}

        # 设置日志级别
        logger.set_log_level(log_level)
        self.log_level = log_level

        # ⭐ 兼容：schema 既可以是 list(fields)，也可以是 dict({fields, submit})
        if isinstance(schema, dict):
            fields_json = list(schema.get("fields", []))
            submit_json = schema.get("submit")
            if submit_json:
                # submit 当字段加载，但默认不渲染
                submit_json = dict(submit_json)
                submit_json.setdefault("name", submit_json.get("key", "submit"))
                submit_json.setdefault("type", "hidden")
                submit_json.setdefault("visible", False)
                submit_json.setdefault("render", False)  # 若你加了 render
                fields_json.append(submit_json)
        else:
            fields_json = schema

        for f in fields_json:
            field = Field(f)
            self.fields[field.key] = field
            self.values[field.key] = field.value

        self.methods = {

        }

    def set_log_level(self, level: int):
        """
        设置日志级别
        0: 无输出
        1: 仅错误
        2: 警告 + 错误 (默认)
        3: 调试 + 警告 + 错误
        4: 详细 + 调试 + 警告 + 错误
        """
        logger.set_log_level(level)
        self.log_level = level


    def _get_visible_values(self) -> dict:
        """
        获取所有可见字段的值（平铺格式）
        
        Returns:
            dict: 包含所有可见字段键值对的字典
        """
        return {
            k: v for k, v in self.values.items()
            if k in self.fields and self.fields[k].visible
        }

    def _get_visible_values_tree(self) -> dict:
        """
        获取所有可见字段的值（嵌套树格式）
        
        Returns:
            dict: 包含所有可见字段键值对的嵌套字典
        """
        visible_values = self._get_visible_values()
        root = {}
        for k, v in visible_values.items():
            _set_nested(root, k.split(self.key_sep), v)
        return root

    def _values_tree(self) -> dict:
        """
        内部使用：返回所有字段的值（嵌套树格式），包括隐藏字段
        
        Returns:
            dict: 包含所有字段键值对的嵌套字典
        """
        root = {}
        for k, v in self.values.items():
            _set_nested(root, k.split(self.key_sep), v)
        return root

    def _process_field_rules(self, field_key: str, updated_keys: set, user_input_requests: list):
        """
        处理指定字段的规则
        
        Args:
            field_key: 字段键名
            updated_keys: 已更新字段集合
            user_input_requests: 用户输入请求列表
        """
        field = self.fields[field_key]

        for rule in field.rules:
            if self._evaluate_condition(rule.get("if")):
                self._execute_then(rule.get("then", []), updated_keys, user_input_requests)
                continue

            handled = False
            for br in rule.get("elif", []) or []:
                if self._evaluate_condition(br.get("if")):
                    self._execute_then(br.get("then", []), updated_keys, user_input_requests)
                    handled = True
                    break

            if (not handled) and ("else" in rule):
                self._execute_then(rule.get("else", []), updated_keys, user_input_requests)

    def _execute_then(self, cmds: List[str], updated_keys: set, user_input_requests: list):
        """
        执行 then 指令列表，捕获异常并写入对应字段的 errors
        
        Args:
            cmds: 指令列表
            updated_keys: 已更新字段集合
            user_input_requests: 用户输入请求列表
        """
        for cmd in cmds:
            try:
                instr = self._parse_instruction(cmd)
                if not instr:
                    continue

                t = instr["type"]
                if t == "call_method":
                    self._execute_call_method(instr, updated_keys)

                elif t == "call_method_multi":
                    self._execute_call_method_multi(instr, updated_keys)
                
                elif t == "call_method_to_temp":
                    # ⭐ 新增：将方法返回结果存到临时变量
                    self._execute_call_method_to_temp(instr)

                elif t == "conditional_action":
                    # ⭐ 新增：条件执行（if ... then ...）
                    self._execute_conditional_action(instr, updated_keys, user_input_requests)

                elif t == "clear":
                    key, prop = instr["target"], instr["prop"]
                    self._clear(key, prop, updated_keys)

                elif t == "set":
                    key, prop = instr["target"], instr["prop"]
                    if "expression" in instr:
                        # 新版：表达式求值
                        self._set(key, prop, instr["expression"], updated_keys, is_expression=True)
                    else:
                        # 旧版：直接赋值（兼容）
                        self._set(key, prop, instr.get("value"), updated_keys, is_expression=False)

                elif t == "emit":
                    if instr["event"] == "agent.request_user_input":
                        user_input_requests.append(instr.get("payload", ""))

            except Exception as e:
                # 捕获异常，写入相关字段的 errors
                
                error_msg = f"执行指令失败: {cmd}, 错误: {str(e)}"
                logger.error(error_msg)
                logger.error(f"[堆栈跟踪] {traceback.format_exc()}")
                # 尝试从指令中提取目标字段
                target_key = None
                if instr and instr.get("target"):
                    target_key = instr["target"]
                elif instr and instr.get("target_field"):
                    target_key = instr["target_field"]

                if target_key and target_key in self.fields:
                    self.fields[target_key].errors = error_msg
                    updated_keys.add(target_key)

    def _get_affected_fields(self, start_key: str) -> List[str]:
        """
        获取受指定字段影响的其他字段列表
        
        Args:
            start_key: 起始字段键名
            
        Returns:
            List[str]: 受影响的字段键名列表
        """
        visited = set()
        queue = deque([start_key])
        result = []

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            for key, field in self.fields.items():
                if current in field.dependencies and key not in visited:
                    queue.append(key)
                    result.append(key)

        return result

    # ---------------- 嵌套支持：条件 eval 上下文 ----------------
    def _evaluate_condition(self, expr: Optional[str]) -> bool:
        """
        评估条件表达式
        
        Args:
            expr: 条件表达式字符串
            
        Returns:
            bool: 条件评估结果
        """
        if not expr:
            return True

        try:
            expr = expr.strip()
            expr = expr.replace(" != null", " is not None")
            expr = expr.replace(" == null", " is None")
            expr = expr.replace(" == true", " == True")
            expr = expr.replace(" == false", " == False")

            # 1) 直接字段值：提供平铺+嵌套两套访问方式
            values_flat = dict(self.values)
            values_tree = _build_attr_tree(values_flat, sep=self.key_sep)

            # 2) 字段视图（可访问 options/visible/...），同样提供嵌套树
            f_flat = {k: _FieldView(v) for k, v in self.fields.items()}
            f_tree = _build_attr_tree(f_flat, sep=self.key_sep)

            # ⭐ 3) 临时变量（支持点访问）
            temp_vars_tree = _build_attr_tree(self.temp_vars, sep=".")

            # locals：
            # - 让表达式可以直接写 a.b（取 value）
            # - 让表达式可以写 f.a.b.options（取字段状态）
            # - 让表达式可以写 temp_result.code（取临时变量）
            local = {}
            local.update(values_tree)   # 字段值
            local.update(temp_vars_tree)  # 临时变量
            local["values"] = values_flat
            local["f"] = f_tree
            local["fields"] = f_tree

            safe_globals = {
                "__builtins__": {},
                "len": len,
                "min": min,
                "max": max,
                "sum": sum,
                "any": any,
                "all": all,
                "sorted": sorted,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "re": re,
            }

            return bool(eval(expr, safe_globals, local))

        except Exception as e:
            logger.error(f"条件评估失败: {expr}, 错误: {e}")
            return False

    # ---------------- 辅助方法：解析方法参数 ----------------
    def _parse_method_params(self, params_str: str) -> Union[list, dict]:
        """
        解析方法调用的参数（支持位置参数和命名参数）
        
        Args:
            params_str: 参数字符串
            
        Returns:
            Union[list, dict]: 
                - 如果包含命名参数（key=value），返回字典 {key: value}
                - 否则返回位置参数列表 [value1, value2, ...]
        
        Examples:
            "releasePlanId=releasePlanId, region=changeRegion" -> {"releasePlanId": 1109, "region": "cn-hangzhou"}
            "changeRegion, buildVersion" -> ["cn-hangzhou", "v1.0.0"]
        """
        if not params_str:
            return []
        
        # 检测是否包含命名参数（key=value格式）
        has_named_params = '=' in params_str and not (params_str.strip().startswith("'") or params_str.strip().startswith('"'))
        
        if has_named_params:
            return self._parse_named_params(params_str)
        else:
            return self._parse_positional_params(params_str)
    
    def _parse_named_params(self, params_str: str) -> dict:
        """
        解析命名参数格式：key1=value1, key2=value2
        
        Examples:
            "releasePlanId=releasePlanId, region=changeRegion"
        """
        result = {}
        
        for param in [x.strip() for x in params_str.split(",")]:
            if '=' not in param:
                continue
            
            # 分割键值对
            key, value_expr = param.split('=', 1)
            key = key.strip()
            value_expr = value_expr.strip()
            
            # 解析值表达式
            value = self._resolve_param_value(value_expr)
            result[key] = value
        
        return result
    
    def _parse_positional_params(self, params_str: str) -> list:
        """
        解析位置参数格式：value1, value2, value3
        
        Examples:
            "region, app.service, 1001"
        """
        params = []
        
        for p in [x.strip() for x in params_str.split(",")]:
            value = self._resolve_param_value(p)
            params.append(value)
        
        return params
    
    def _resolve_param_value(self, expr: str) -> Any:
        """
        解析参数值表达式，支持：
        - 字段引用：region, app.region
        - 字段值引用：region.value
        - 字面量：'string', 123, true, false, null
        """
        expr = expr.strip()
        
        # 处理 .value 后缀
        if expr.endswith(".value"):
            field_key = expr[:-6]
            return self.values.get(field_key)
        
        # 检查是否是字段引用
        if expr in self.values:
            return self.values.get(expr)
        
        # 检查是否是嵌套字段引用（包含分隔符）
        if self.key_sep in expr and expr in self.values:
            return self.values.get(expr)
        
        # 尝试作为字面量解析
        try:
            literal = expr.replace("null", "None") \
                         .replace("true", "True") \
                         .replace("false", "False")
            return eval(literal, {"__builtins__": {}}, {})
        except:
            return expr

    def _eval_expression(self, expr: str) -> Any:
        """
        安全地求值表达式，支持字段引用和 Python 表达式
        
        Args:
            expr: 表达式字符串
            
        Returns:
            Any: 表达式的求值结果
        
        例如：
        - f"{app.name}-{app.region}"
        - app.service.value.upper()
        - app.count.value + 1
        - temp_result.data.name  # ⭐ 支持临时变量
        """
        expr = expr.strip()
        
        # 简单的字面量替换
        expr = expr.replace("null", "None").replace("true", "True").replace("false", "False")
        
        # 构建求值上下文
        values_flat = dict(self.values)
        values_tree = _build_attr_tree(values_flat, sep=self.key_sep)
        
        # 字段视图
        f_flat = {k: _FieldView(v) for k, v in self.fields.items()}
        f_tree = _build_attr_tree(f_flat, sep=self.key_sep)
        
        # ⭐ 临时变量
        temp_vars_tree = _build_attr_tree(self.temp_vars, sep=".")
        
        local = {}
        local.update(values_tree)  # 字段值
        local.update(temp_vars_tree)  # 临时变量
        local["values"] = values_flat
        local["f"] = f_tree
        local["fields"] = f_tree
        
        safe_globals = {
            "__builtins__": {},
            "len": len,
            "min": min,
            "max": max,
            "sum": sum,
            "any": any,
            "all": all,
            "sorted": sorted,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "re": re,
        }
        
        try:
            return eval(expr, safe_globals, local)
        except Exception as e:
            # 如果求值失败，尝试作为字符串字面量
            logger.warning(f"表达式求值失败: {expr}, 错误: {e}")
            return expr.strip("'").strip('"')

    # ---------------- 指令解析（支持嵌套 key） ----------------
    def _parse_instruction(self, cmd: str) -> Optional[dict]:
        """
        解析指令字符串为结构化字典
        
        Args:
            cmd: 指令字符串
            
        Returns:
            Optional[dict]: 解析后的指令字典，如果解析失败返回 None
        """
        cmd = cmd.strip()

        # ⭐ 新增：解析 "if ... then ..." 格式
        # 示例：if temp_result.code == 200 then set service.options = temp_result.data
        if cmd.startswith("if ") and " then " in cmd:
            parts = cmd.split(" then ", 1)
            if len(parts) == 2:
                condition = parts[0][3:].strip()  # 去掉 "if "
                action = parts[1].strip()
                return {
                    "type": "conditional_action",
                    "condition": condition,
                    "action": action
                }

        # call_method 支持三种格式：
        # 1. 单目标：call_method fn() -> field.prop
        # 2. 多目标：call_method fn() -> {field1.prop: path1, field2.prop: path2}
        # 3. ⭐ 临时变量：call_method fn() -> temp_var
        if cmd.startswith("call_method "):
            # 先尝试匹配多目标格式
            multi_match = re.match(
                r'call_method\s+(\w+)\(([^)]*)\)\s*->\s*\{([^}]+)\}',
                cmd
            )
            if multi_match:
                method_name = multi_match.group(1)
                params_str = multi_match.group(2).strip()
                targets_str = multi_match.group(3).strip()

                # 解析参数
                params = self._parse_method_params(params_str)

                # 解析多个目标映射
                targets = {}
                for mapping in targets_str.split(','):
                    if ':' not in mapping:
                        continue
                    target_part, path_part = mapping.split(':', 1)
                    target_part = target_part.strip()
                    path_part = path_part.strip()

                    # 解析 field.prop
                    if '.' in target_part:
                        parts = target_part.rsplit('.', 1)
                        target_field = parts[0]
                        target_prop = parts[1]
                    else:
                        continue

                    # 解析路径 data.services
                    path_parts = [p for p in path_part.split('.') if p]

                    targets[f"{target_field}.{target_prop}"] = path_parts

                return {
                    "type": "call_method_multi",
                    "method": method_name,
                    "params": params,
                    "targets": targets
                }

            # ⭐ 新增：尝试匹配临时变量格式（没有 . 的目标名）
            # call_method get_services(region) -> temp_result
            temp_match = re.match(
                r'call_method\s+(\w+)\(([^)]*)\)\s*->\s*(\w+)$',
                cmd
            )
            if temp_match:
                method_name = temp_match.group(1)
                params_str = temp_match.group(2).strip()
                temp_var_name = temp_match.group(3)

                params = self._parse_method_params(params_str)

                return {
                    "type": "call_method_to_temp",
                    "method": method_name,
                    "params": params,
                    "temp_var": temp_var_name
                }

            # 尝试匹配单目标格式（带 . 的字段名）
            single_match = re.match(
                r'call_method\s+(\w+)\(([^)]*)\)((?:\.\w+)*)\s*->\s*([\w.]+)\.(\w+)',
                cmd
            )
            if single_match:
                method_name = single_match.group(1)
                params_str = single_match.group(2).strip()
                result_path = single_match.group(3)
                target_field = single_match.group(4)
                target_prop = single_match.group(5)

                # 解析参数
                params = self._parse_method_params(params_str)

                # 解析结果路径
                path_parts = []
                if result_path:
                    path_parts = [p for p in result_path.split('.') if p]

                return {
                    "type": "call_method",
                    "method": method_name,
                    "params": params,
                    "result_path": path_parts,
                    "target_field": target_field,
                    "target_prop": target_prop
                }

        # clear app.service.value / clear a.b.options
        if cmd.startswith("clear "):
            parts = cmd[6:].strip().split(".")
            if len(parts) >= 2:
                prop = parts[-1]
                key = ".".join(parts[:-1])
                if prop in ("value", "options"):
                    return {"type": "clear", "target": key, "prop": prop}

        # set 指令增强：支持字段引用和 Python 表达式
                # set 指令增强：支持字段引用和 Python 表达式
        if cmd.startswith("set "):
            # 1) 先支持：set field = expr   （默认写 value）
            m0 = re.match(r"set\s+([\w.]+)\s*=\s*(.+)$", cmd)
            if m0 and "." not in m0.group(1):  # 避免和下面 field.prop 冲突
                key, raw = m0.group(1), m0.group(2).strip()
                return {"type": "set", "target": key, "prop": "value", "expression": raw}

            # 2) 原有：set field.prop = expr
            m = re.match(r"set\s+([\w.]+)\.(\w+)\s*=\s*(.+)$", cmd)
            if m:
                key, prop, raw = m.group(1), m.group(2), m.group(3).strip()
                return {"type": "set", "target": key, "prop": prop, "expression": raw}


        # emit agent.request_user_input('a.b.c')
        if cmd.startswith("emit "):
            match = re.match(r"emit\s+([\w.]+)\('([^']+)'\)", cmd)
            if match:
                return {"type": "emit", "event": match.group(1), "payload": match.group(2)}

        return None

    # ---------------- 执行动作（支持嵌套 key） ----------------
    def _clear(self, key: str, prop: str, updated_keys: set):
        """
        清空指定字段的属性值
        
        Args:
            key: 字段键名
            prop: 属性名称（value 或 options）
            updated_keys: 已更新字段集合
        """
        if key not in self.fields:
            return
        f = self.fields[key]
        if prop == "value":
            f.value = None
            self.values[key] = None
        elif prop == "options":
            f.options = None
        updated_keys.add(key)

    def _set(self, key: str, prop: str, val: Any, updated_keys: set, is_expression: bool = False):
        """
        设置指定字段的属性值
        
        Args:
            key: 字段键名
            prop: 属性名称（value, options, visible, disabled, required, errors）
            val: 要设置的值
            updated_keys: 已更新字段集合
            is_expression: 是否为表达式，如果是则需要先求值
        """
        if key not in self.fields:
            return
        f = self.fields[key]
        
        # 如果是表达式，需要先求值
        if is_expression and isinstance(val, str):
            try:
                val = self._eval_expression(val)
            except Exception as e:
                error_msg = f"表达式求值失败: {val}, 错误: {str(e)}"
                logger.error(error_msg)
                logger.error(f"[堆栈跟踪] {traceback.format_exc()}")
                f.errors = error_msg
                updated_keys.add(key)
                return
        
        if prop == "value":
            f.value = val
            self.values[key] = val
        elif prop == "options":
            f.options = val
        elif prop == "visible":
            f.visible = bool(val)
        elif prop == "disabled":
            f.disabled = bool(val)
        elif prop == "required":
            f.required = bool(val)
        elif prop == "errors":
            f.errors = str(val) if val else ""
        updated_keys.add(key)

    def _execute_call_method_to_temp(self, instr: dict):
        """
        执行方法并将结果存储到临时变量（支持命名参数）
        
        Args:
            instr: 指令字典，包含 method, params, temp_var
        """
        method_name = instr["method"]
        params = instr["params"]
        temp_var = instr["temp_var"]

        if method_name not in self.methods:
            error_msg = f"未注册的方法: {method_name}"
            logger.error(error_msg)
            # 将错误存储到临时变量
            self.temp_vars[temp_var] = {"error": error_msg}
            return

        method = self.methods[method_name]
        try:
            # ⭐ 支持命名参数：如果 params 是字典，使用 **kwargs 传递
            if isinstance(params, dict):
                logger.debug(f"调用 {method_name}(**{params})")
                result = method(**params)
            else:
                logger.debug(f"调用 {method_name}(*{params})")
                result = method(*params)

            # 将结果存储到临时变量
            self.temp_vars[temp_var] = result
            logger.debug(f"临时变量 {temp_var} = {result}")
        except Exception as e:
            error_msg = f"执行 {method_name} 失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"[堆栈跟踪] {traceback.format_exc()}")
            self.temp_vars[temp_var] = {"error": error_msg}

    def _execute_conditional_action(self, instr: dict, updated_keys: set, user_input_requests: list):
        """
        执行条件判断指令
        
        Args:
            instr: 指令字典，包含 condition 和 action
            updated_keys: 已更新字段集合
            user_input_requests: 用户输入请求列表
        
        格式：if condition then action
        """
        condition = instr["condition"]
        action = instr["action"]

        # 评估条件
        if self._evaluate_condition(condition):
            # 条件为真，执行动作
            logger.debug(f"条件 '{condition}' 为真，执行: {action}")
            # 递归执行动作（可能是 set/clear/call_method 等）
            self._execute_then([action], updated_keys, user_input_requests) if action else None
        else:
            logger.debug(f"条件 '{condition}' 为假，跳过: {action}")

    def _execute_call_method_multi(self, instr: dict, updated_keys: set):
        """
        执行多目标映射的 call_method
        
        Args:
            instr: 指令字典，包含 method, params, targets
            updated_keys: 已更新字段集合
        
        targets: {"field1.prop": ["path", "to", "value"], "field2.prop": ["path2"]}
        """
        method_name = instr["method"]
        params = instr["params"]
        targets = instr["targets"]

        if method_name not in self.methods:
            error_msg = f"未注册的方法: {method_name}"
            logger.error(error_msg)
            # 将错误写入所有目标字段
            for target_spec in targets.keys():
                if '.' in target_spec:
                    field_key = target_spec.rsplit('.', 1)[0]
                    if field_key in self.fields:
                        self.fields[field_key].errors = error_msg
                        updated_keys.add(field_key)
            return

        method = self.methods[method_name]
        try:
            result = method(*params)

            # 遍历所有目标进行映射
            for target_spec, path_parts in targets.items():
                if '.' not in target_spec:
                    continue

                field_key, prop = target_spec.rsplit('.', 1)
                if field_key not in self.fields:
                    continue

                # 提取路径值
                extracted_value = result
                if path_parts:
                    for part in path_parts:
                        if isinstance(extracted_value, dict):
                            extracted_value = extracted_value.get(part)
                        elif isinstance(extracted_value, (list, tuple)) and part.isdigit():
                            idx = int(part)
                            extracted_value = extracted_value[idx] if idx < len(extracted_value) else None
                        else:
                            error_msg = f"无法从返回结果中访问路径: {'.'.join(path_parts)}"
                            logger.error(error_msg)
                            self.fields[field_key].errors = error_msg
                            updated_keys.add(field_key)
                            extracted_value = None
                            break

                if extracted_value is None and path_parts:
                    continue

                # 赋值给目标字段
                target_field = self.fields[field_key]
                target_field.errors = ""

                if prop == "options":
                    if isinstance(extracted_value, list):
                        if all(isinstance(x, dict) and "label" in x and "value" in x for x in extracted_value):
                            target_field.options = extracted_value
                        else:
                            target_field.options = [{"label": str(x), "value": x} for x in extracted_value]
                    else:
                        target_field.options = []

                elif prop == "value":
                    target_field.value = extracted_value
                    self.values[field_key] = extracted_value

                elif prop in ("visible", "disabled", "required"):
                    setattr(target_field, prop, bool(extracted_value))

                elif prop == "errors":
                    target_field.errors = str(extracted_value) if extracted_value else ""

                updated_keys.add(field_key)

        except Exception as e:
            error_msg = f"执行 {method_name} 失败: {str(e)}"
            logger.error(error_msg)

            logger.error(f"[堆栈跟踪] {traceback.format_exc()}")

            # 将错误写入所有目标字段
            for target_spec in targets.keys():
                if '.' in target_spec:
                    field_key = target_spec.rsplit('.', 1)[0]
                    if field_key in self.fields:
                        self.fields[field_key].errors = error_msg
                        updated_keys.add(field_key)

    def _execute_call_method(self, instr: dict, updated_keys: set):
        """
        执行单目标的 call_method 指令
        
        Args:
            instr: 指令字典，包含 method, params, result_path, target_field, target_prop
            updated_keys: 已更新字段集合
        """
        method_name = instr["method"]
        params = instr["params"]
        result_path = instr.get("result_path", [])
        target_field_key = instr["target_field"]
        target_prop = instr["target_prop"]

        if method_name not in self.methods:
            error_msg = f"未注册的方法: {method_name}"
            logger.error(error_msg)
            if target_field_key in self.fields:
                self.fields[target_field_key].errors = error_msg
                updated_keys.add(target_field_key)
            return

        method = self.methods[method_name]
        try:
            result = method(*params)

            # 如果指定了结果路径，从嵌套数据中提取值
            if result_path:
                for part in result_path:
                    if isinstance(result, dict):
                        result = result.get(part)
                    elif isinstance(result, (list, tuple)) and part.isdigit():
                        idx = int(part)
                        result = result[idx] if idx < len(result) else None
                    else:
                        error_msg = f"无法从返回结果中访问路径: {'.'.join(result_path)}"
                        logger.error(error_msg)
                        if target_field_key in self.fields:
                            self.fields[target_field_key].errors = error_msg
                            updated_keys.add(target_field_key)
                        return

            if target_field_key not in self.fields:
                return
            target_field = self.fields[target_field_key]

            # 清除之前的错误信息（执行成功）
            target_field.errors = ""

            if target_prop == "options":
                if isinstance(result, list):
                    if all(isinstance(x, dict) and "label" in x and "value" in x for x in result):
                        target_field.options = result
                    else:
                        target_field.options = [{"label": str(x), "value": x} for x in result]
                else:
                    target_field.options = []

            elif target_prop == "value":
                target_field.value = result
                self.values[target_field_key] = result

            elif target_prop in ("visible", "disabled", "required"):
                setattr(target_field, target_prop, bool(result))

            elif target_prop == "errors":
                target_field.errors = str(result) if result else ""

            updated_keys.add(target_field_key)

        except Exception as e:
            error_msg = f"执行 {method_name} 失败: {str(e)}"
            logger.error(error_msg)

            logger.error(f"[堆栈跟踪] {traceback.format_exc()}")

            # 将错误信息写入目标字段
            if target_field_key in self.fields:
                self.fields[target_field_key].errors = error_msg
                updated_keys.add(target_field_key)
    def init(self) -> dict:
        """
        【外部接口】初始化所有字段，执行每个字段规则中的 init 指令
        
        Returns:
            dict: 包含初始化结果的字典
            {
                "updated_fields": list,        # 所有被更新的字段 key 列表
                "updated_field_values": dict,  # 更新的字段值
                "get_fields_for_agent": list,  # 字段信息列表
                "validate": dict,              # 校验结果
            }
        """
        # 清空临时变量
        self.temp_vars = {}
        
        updated_keys = set()
        user_input_requests = []
        
        # 遍历所有字段，执行每个规则中的 init 指令
        for field_key in self.fields:
            field = self.fields[field_key]
            for rule in field.rules:
                # 执行 init 指令（无条件执行）
                init_cmds = rule.get("init", [])
                if init_cmds:
                    self._execute_then(init_cmds, updated_keys, user_input_requests)
        
        return {
            "updated_fields": list(updated_keys),
            "updated_field_values": {
                k: self.values.get(k) for k in updated_keys
            },
            "get_fields_for_agent": self.get_fields_for_agent(),
            "validate": self.validate(),
        }
    
    def on_field_change(self, changed_key: str, new_value: Any) -> dict:
        """
        【外部接口】处理字段变化事件，执行规则并返回更新结果
        Args:
            changed_key: 发生变化的字段键名
            new_value: 字段的新值
        Returns:
            dict: 包含更新结果的字典
            {
                "updated_fields": list,        # 所有被更新的字段 key 列表
                "visible_fields": list,        # 只包含可见字段的 key 列表
                "requests_user_input": list,   # 用户输入请求列表
                "field_states": dict,          # 可见字段的状态详情
                "all_values": dict,            # 只包含可见字段的值（平铺）
                "all_values_tree": dict,       # 只包含可见字段的值（嵌套树）
            }
        """
        if changed_key not in self.fields:
            return {"error": f"字段 {changed_key} 不存在"}
        self.values[changed_key] = new_value
        self.fields[changed_key].value = new_value
        # 清空临时变量（每次字段变化时重置）
        self.temp_vars = {}
        updated_keys = set()
        user_input_requests = []
        self._process_field_rules(changed_key, updated_keys, user_input_requests)
        affected_keys = self._get_affected_fields(changed_key)
        for key in affected_keys:
            self._process_field_rules(key, updated_keys, user_input_requests)
        # 过滤掉隐藏的字段
        visible_updated_keys = [k for k in updated_keys if self.fields[k].visible]
        return {
            "updated_fields": list(updated_keys),           # 所有更新的字段（包括隐藏的）
            
            # "visible_fields": visible_updated_keys,         # 只包含可见的字段
            # "requests_user_input": user_input_requests if user_input_requests else None,
            # "field_states": {
            #     k: {
            #         "value": self.fields[k].value,
            #         "options": self.fields[k].options,
            #         "visible": self.fields[k].visible,
            #         "disabled": self.fields[k].disabled,
            #         "required": self.fields[k].required,
            #         "errors": self.fields[k].errors,
            #     }
            #     for k in visible_updated_keys  # 只返回可见字段的状态
            # },
            # 平铺 values（只包含可见字段）
            # "all_values": self._get_visible_values(),
            "updated_field_values": {
                k: self.values.get(k) for k in updated_keys
            },
            "get_fields_for_agent": self.get_fields_for_agent(),
            "validate": self.validate(),
            # 嵌套树 values（只包含可见字段）
            # "all_values_tree": self._get_visible_values_tree(),
        }

    def validate(self) -> Dict[str, Any]:
        """
        【外部接口】校验所有字段，检查 required=True 的字段是否有有效值。
        注意：只校验可见字段（visible=True）
        
        Returns:
            Dict[str, Any]: 校验结果
            {
                "valid": bool,           # 整体是否通过校验
                "errors": {              # 各字段的错误信息
                    "field_key": "error_message",
                    ...
                },
                "invalid_fields": []     # 未通过校验的字段 key 列表
            }
        """
        validation_errors = {}
        invalid_fields = []
        
        for key, field in self.fields.items():
            # 只校验 required=True 且可见的字段
            if field.required and field.visible:
                value = field.value
                
                # 检查值是否为空
                is_empty = (
                    value is None or
                    value == "" or
                    (isinstance(value, list) and len(value) == 0)
                )
                
                if is_empty:
                    validation_errors[key] = f"{field.name} 必填"
                    invalid_fields.append(key)
        
        return {
            "valid": len(invalid_fields) == 0,
            "errors": validation_errors,
            "invalid_fields": invalid_fields
        }

    def get_all_visible_fields(self) -> Dict[str, Dict[str, Any]]:
        """
        【外部接口】获取所有可见字段的详情（用于渲染表单）
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有可见字段的详细信息字典
        """
        return {
            key: {
                "key": field.key,
                "name": field.name,
                "type": field.type,
                "value": field.value,
                "description": field.description,
                "options": field.options,
                "visible": field.visible,
                "disabled": field.disabled,
                "required": field.required,
                "errors": field.errors,
            }
            for key, field in self.fields.items()
            if field.visible
        }

    def get_fields_for_agent(self) -> List[Dict[str, Any]]:
        """
        【外部接口】获取所有字段的简化信息，专为 AI Agent 使用
        
        Returns:
            List[Dict[str, Any]]: 包含关键字段信息的列表
            [
                {
                    "key": str,          # 字段唯一标识
                    "name": str,         # 字段显示名称
                    "value": Any,        # 字段当前值
                    "type": str,         # 字段类型
                    "errors": str,       # 错误信息
                    "required": bool,    # 是否必填
                    "description": str,  # 字段描述
                },
                ...
            ]
        """
        return [
                {
                    "key": field.key,
                    "name": field.name,
                    "value": field.value,
                    "type": field.type,
                    "errors": field.errors,
                    "required": field.required,
                    "description": field.description,
                    **({"options": field.options} if field.options is not None and field.options else {})
                }
                for key, field in self.fields.items()
                ]
    def check_submit(self, submit_key: str = "can_submit") -> Dict[str, Any]:
        """
        执行 submit 字段规则，判断是否可提交。
        返回：
        {
          "can_submit": bool,
          "submit_key": str,
          "errors": str,              # submit 字段自身 errors（若有）
          "updated_fields": list,
          "updated_field_values": dict
        }
        """
        if submit_key not in self.fields:
            return {"can_submit": False, "submit_key": submit_key, "errors": f"submit 字段不存在: {submit_key}"}

        # 不清空 values，但清空 temp_vars（避免脏数据）
        self.temp_vars = {}

        updated_keys = set()
        user_input_requests = []  # submit 不需要，但 _execute_then 签名要

        # ⭐ 执行 submit 字段自己的 rules
        self._process_field_rules(submit_key, updated_keys, user_input_requests)

        # ⭐ 读取结果
        f = self.fields[submit_key]
        can = bool(f.value)

        # 如果你希望失败时给固定错误信息，可在这里覆盖
        err = f.errors
        if (not can) and (not err):
            err = "条件未满足，暂不可提交"

        return {
            "can_submit": can,
            "submit_key": submit_key,
            "errors": err,
            "updated_fields": list(updated_keys),
            "updated_field_values": {k: self.values.get(k) for k in updated_keys},
        }

