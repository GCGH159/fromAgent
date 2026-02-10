# FormAgent

一个强大的动态表单引擎，支持复杂的字段规则、依赖关系和条件逻辑。现已整合 LangChain 1.2，提供智能对话式表单管理能力。

## 功能特性

### 核心功能

- **动态表单管理**：支持动态创建和管理表单字段
- **字段规则引擎**：支持 if/elif/else 条件逻辑
- **依赖关系追踪**：自动追踪字段间的依赖关系，实现级联更新
- **嵌套字段支持**：支持点号分隔的嵌套字段访问（如 `app.region`）
- **多种字段类型**：支持 text、select、radio、hidden 等多种字段类型
- **动态验证**：支持必填、禁用、可见性等动态属性控制

### LangChain 整合特性

- **智能对话接口**：通过自然语言与表单交互
- **对话记忆**：支持持续性对话，记住上下文
- **多会话管理**：支持创建和管理多个会话
- **工具调用**：将表单操作封装为 LangChain 工具
- **LLM 驱动**：使用大语言模型理解用户意图

### 高级特性

- **日志控制**：多级别日志输出（无输出/错误/警告/调试/详细）
- **方法调用**：支持在规则中调用自定义方法
- **临时变量**：支持将方法结果存入临时变量供后续使用
- **条件动作**：支持嵌套的条件执行逻辑
- **表达式求值**：支持 Python 表达式求值
- **字段视图**：提供只读的字段状态访问接口

## 快速开始

### 安装

1. **克隆仓库**
```bash
git clone git@github.com:GCGH159/fromAgent.git
cd FormAgent
```

2. **创建 Python 虚拟环境（Python 3.11）**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 OpenAI API Key
```

### 基本使用

#### 使用 DynamicFormEngine（核心引擎）

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

#### 使用 LangChain Agent（智能对话）

```python
from app.core.form_agent import FormAgentWithMemory

# 创建 Agent
agent = FormAgentWithMemory()

# 与 Agent 对话
response = agent.chat("帮我加载一个表单结构，包含姓名、年龄等字段")
print(response)

response = agent.chat("设置姓名为张三")
print(response)

response = agent.chat("查看所有字段的值")
print(response)
```

#### 命令行交互模式

```bash
# 启动交互模式
python main.py

# 运行演示模式
python main.py --demo

# 查看帮助
python main.py --help
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

## LangChain Agent 使用指南

### 可用工具

FormAgent 提供以下 LangChain 工具：

1. **load_schema** - 加载表单结构定义
2. **set_field_value** - 设置字段值
3. **get_field_value** - 获取字段值
4. **get_all_values** - 获取所有可见字段的值（平铺格式）
5. **get_all_values_tree** - 获取所有可见字段的值（嵌套树格式）
6. **get_field_info** - 获取字段详细信息
7. **list_all_fields** - 列出所有字段
8. **set_field_visibility** - 设置字段可见性
9. **set_field_required** - 设置字段是否必填
10. **get_field_dependencies** - 获取字段依赖关系
11. **get_affected_fields** - 获取受影响字段
12. **set_log_level** - 设置日志级别

### 对话示例

```
🤖 FormAgent > 帮我加载一个表单结构，包含姓名、年龄、区域等字段
✅ 表单结构加载成功，共 3 个字段

🤖 FormAgent > 设置姓名为张三
✅ 字段 name 的值已设置为: 张三

🤖 FormAgent > 设置年龄为25
✅ 字段 age 的值已设置为: 25

🤖 FormAgent > 把区域设置为杭州
✅ 字段 region 的值已设置为: cn-hangzhou

🤖 FormAgent > 查看所有字段的值
✅ 所有可见字段的值:
{
  "name": "张三",
  "age": 25,
  "region": "cn-hangzhou"
}

🤖 FormAgent > 隐藏年龄字段
✅ 字段 age 已设置为隐藏

🤖 FormAgent > 设置姓名为必填
✅ 字段 name 已设置为必填
```

### 会话管理

```python
from app.core.form_agent import create_session

# 创建新会话
agent = create_session()

# 获取会话 ID
session_id = agent.get_session_id()

# 清空会话历史
agent.clear_history()

# 获取消息数量
count = agent.get_message_count()

# 获取会话信息
info = agent.get_session_info()
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

### FormAgentWithMemory 类

#### 构造函数

```python
FormAgentWithMemory(session_id: Optional[str] = None)
```

**参数说明：**
- `session_id`: 会话 ID，如果为 None 则自动生成

#### 主要方法

##### chat(user_input: str) -> str

与 Agent 对话

```python
response = agent.chat("设置姓名为张三")
```

##### get_session_id() -> str

获取当前会话 ID

```python
session_id = agent.get_session_id()
```

##### clear_history()

清空当前会话的对话历史

```python
agent.clear_history()
```

##### get_message_count() -> int

获取当前会话的消息数量

```python
count = agent.get_message_count()
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
├── agentFrom.py              # 核心表单引擎实现
├── config.py                 # 配置文件
├── main.py                  # 主入口文件
├── requirements.txt          # 依赖列表
├── .env.example             # 环境变量示例
├── README.md                # 项目文档
└── app/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── chat_history.py  # 对话历史管理
    │   └── form_agent.py    # LangChain Agent 实现
    └── tools/
        ├── __init__.py
        └── form_tools.py    # LangChain 工具函数
```

## 依赖项

### 核心依赖

- Python 3.11+
- 标准库：`typing`, `collections`, `re`, `traceback`, `logging`

### LangChain 依赖

- `langchain==1.2.0` - LangChain 核心库
- `langchain-core==1.2.0` - LangChain 核心模块
- `langchain-openai==1.2.0` - OpenAI 集成
- `openai==1.58.1` - OpenAI SDK
- `pydantic==2.10.3` - 数据验证
- `pydantic-settings==2.6.1` - 配置管理
- `python-dotenv==1.0.1` - 环境变量管理

## 使用场景

- 动态表单生成
- 复杂的表单验证逻辑
- 字段间的级联更新
- 条件性表单显示
- 数据驱动的表单配置
- 智能对话式表单填写
- 自动化表单数据处理

## 配置说明

### 环境变量

在 `.env` 文件中配置以下变量：

```bash
# LLM 配置
LLM_MODEL=gpt-4o-mini              # 模型名称
LLM_API_KEY=your_api_key_here      # OpenAI API Key
LLM_BASE_URL=https://api.openai.com/v1  # API 基础 URL
LLM_TEMPERATURE=0.7                # 温度参数

# 表单引擎配置
FORM_KEY_SEP=.                     # 嵌套字段分隔符
FORM_LOG_LEVEL=2                   # 日志级别

# 会话配置
SESSION_MAX_MESSAGES=50            # 最大消息数
SESSION_TIMEOUT=3600               # 会话超时时间（秒）

# 调试配置
DEBUG=false                        # 调试模式
```

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 参考资料

- [LangChain 官方文档](https://docs.langchain.com/oss/python/langchain/overview)
- [OpenAI API 文档](https://platform.openai.com/docs)
