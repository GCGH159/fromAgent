# FormAgent

一个强大的动态表单引擎，支持复杂的字段规则、依赖关系和条件逻辑。

## 功能特性

### 核心功能

- **动态表单管理**：支持动态创建和管理表单字段
- **字段规则引擎**：支持 if/elif/else 条件逻辑
- **依赖关系追踪**：自动追踪字段间的依赖关系，实现级联更新
- **嵌套字段支持**：支持点号分隔的嵌套字段访问（如 `app.region`）
- **多种字段类型**：支持 text、select、radio、hidden 等多种字段类型
- **动态验证**：支持必填、禁用、可见性等动态属性控制

### 高级特性

- **日志控制**：多级别日志输出（无输出/错误/警告/调试/详细）
- **方法调用**：支持在规则中调用自定义方法
- **临时变量**：支持将方法结果存入临时变量供后续使用
- **条件动作**：支持嵌套的条件执行逻辑
- **表达式求值**：支持 Python 表达式求值
- **字段视图**：提供只读的字段状态访问接口

## 快速开始

### 基本使用

```python
from agentFrom import DynamicFormEngine

# 定义表单结构
schema = {
    "fields": [
        {
            "key": "region",
            "name": "区域",
            "type": "select",
            "options": [
                {"label": "华东", "value": "cn-hangzhou"},
                {"label": "华北", "value": "cn-beijing"}
            ],
            "value": "cn-hangzhou"
        },
        {
            "key": "app.name",
            "name": "应用名称",
            "type": "text",
            "dependencies": ["region"]
        }
    ]
}

# 创建表单引擎实例
engine = DynamicFormEngine(schema, log_level=3)

# 设置字段值
engine.set_value("region", "cn-beijing")

# 获取所有可见字段的值
values = engine.get_visible_values()
print(values)
```

### 字段规则示例

```python
schema = {
    "fields": [
        {
            "key": "user.type",
            "name": "用户类型",
            "type": "select",
            "options": [
                {"label": "普通用户", "value": "normal"},
                {"label": "VIP用户", "value": "vip"}
            ],
            "rules": [
                {
                    "if": "user.type.value == 'vip'",
                    "then": [
                        "set vip.level.visible = true",
                        "set vip.level.required = true"
                    ],
                    "else": [
                        "set vip.level.visible = false",
                        "set vip.level.required = false"
                    ]
                }
            ]
        },
        {
            "key": "vip.level",
            "name": "VIP等级",
            "type": "select",
            "visible": False,
            "options": [
                {"label": "黄金会员", "value": "gold"},
                {"label": "钻石会员", "value": "diamond"}
            ]
        }
    ]
}
```

## API 文档

### DynamicFormEngine 类

#### 构造函数

```python
DynamicFormEngine(schema: Any, key_sep: str = ".", log_level: int = 3)
```

**参数说明：**
- `schema`: 表单结构定义，可以是字段列表或包含 fields 和 submit 的字典
- `key_sep`: 嵌套字段分隔符，默认为 "."
- `log_level`: 日志级别（0=无输出, 1=错误, 2=警告+错误, 3=调试+警告+错误）

#### 主要方法

##### set_value(key: str, value: Any)

设置字段值并触发相关规则更新

```python
engine.set_value("region", "cn-hangzhou")
```

##### get_value(key: str) -> Any

获取字段值

```python
region = engine.get_value("region")
```

##### get_visible_values() -> dict

获取所有可见字段的值（平铺格式）

```python
values = engine.get_visible_values()
# 返回: {"region": "cn-hangzhou", "app.name": "myapp"}
```

##### get_visible_values_tree() -> dict

获取所有可见字段的值（嵌套树格式）

```python
values = engine.get_visible_values_tree()
# 返回: {"region": "cn-hangzhou", "app": {"name": "myapp"}}
```

##### set_log_level(level: int)

设置日志级别

```python
engine.set_log_level(3)  # 开启调试日志
```

### Field 类

字段对象，包含以下属性：

- `key`: 字段唯一标识
- `name`: 字段展示名称
- `type`: 字段类型
- `value`: 字段当前值
- `options`: 候选项（select/radio 等使用）
- `dependencies`: 依赖字段列表
- `rules`: 规则列表
- `visible`: 是否可见
- `disabled`: 是否禁用
- `required`: 是否必填
- `errors`: 错误信息

## 规则语法

### 条件判断

```python
{
    "if": "region.value == 'cn-hangzhou'",
    "then": [
        "set app.name.visible = true"
    ],
    "elif": [
        {
            "if": "region.value == 'cn-beijing'",
            "then": ["set app.name.visible = false"]
        }
    ],
    "else": [
        "set app.name.visible = false"
    ]
}
```

### 支持的指令

#### set - 设置属性

```python
"set field.key.visible = true"
"set field.key.value = 'default'"
```

#### clear - 清除属性

```python
"clear field.key.value"
```

#### call_method - 调用方法

```python
"call_method getRegions(region)"
"call_method fetchApps(releasePlanId=releasePlanId, region=region)"
```

#### call_method_to_temp - 调用方法并存储结果

```python
"call_method_to_temp temp_result = fetchRegions(region)"
```

#### conditional_action - 条件动作

```python
"conditional_action if region.value == 'cn-hangzhou' then set app.name.visible = true"
```

### 表达式支持

规则中支持以下表达式：

- 字段值引用：`region.value`
- 嵌套字段：`app.region.value`
- 字段属性：`f.region.visible`
- 临时变量：`temp_result.code`
- Python 表达式：`app.count.value + 1`
- 字符串格式化：`f"{app.name}-{app.region}"`

## 日志系统

### 日志级别

- `0`: 无输出
- `1`: 仅错误
- `2`: 警告 + 错误（默认）
- `3`: 调试 + 警告 + 错误

### 使用示例

```python
# 创建引擎时设置日志级别
engine = DynamicFormEngine(schema, log_level=3)

# 动态调整日志级别
engine.set_log_level(1)  # 只显示错误
```

## 项目结构

```
FormAgent/
├── agentFrom.py      # 核心表单引擎实现
└── README.md         # 项目文档
```

## 依赖项

- Python 3.7+
- 标准库：`typing`, `collections`, `re`, `traceback`, `logging`

## 使用场景

- 动态表单生成
- 复杂的表单验证逻辑
- 字段间的级联更新
- 条件性表单显示
- 数据驱动的表单配置

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
