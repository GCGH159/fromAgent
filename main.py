"""
FormAgent 主入口文件
提供命令行交互界面
"""
import sys
from app.core.form_agent import FormAgentWithMemory, create_session
from app.core.chat_history import list_sessions, delete_session, clear_all_sessions
import json


def print_banner():
    """打印欢迎横幅"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║           FormAgent - 智能表单管理助手                    ║
    ║                                                           ║
    ║           基于 LangChain 1.2 + DynamicFormEngine        ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
    可用命令：
    ---------
    交互命令：
    - 直接输入问题或指令与 Agent 对话
    - 输入 'quit' 或 'exit' 退出程序
    - 输入 'clear' 清空当前会话历史
    - 输入 'new' 创建新会话
    - 输入 'sessions' 查看所有会话
    - 输入 'switch <session_id>' 切换会话
    - 输入 'delete <session_id>' 删除会话
    - 输入 'info' 查看当前会话信息
    - 输入 'help' 显示此帮助信息

    示例对话：
    ---------
    1. 加载表单结构：
       "帮我加载一个表单结构，包含姓名、年龄、地址等字段"

    2. 设置字段值：
       "把姓名设置为张三"
       "设置年龄为25"
       "把区域设置为杭州"

    3. 查看字段信息：
       "查看所有字段"
       "查看姓名字段的详细信息"
       "显示所有字段的值"

    4. 控制字段属性：
       "隐藏年龄字段"
       "设置姓名为必填"
       "显示地址字段"

    5. 查询依赖关系：
       "查看姓名字段的依赖"
       "哪些字段会受年龄字段影响"
    """
    print(help_text)


def print_session_info(agent: FormAgentWithMemory):
    """打印会话信息"""
    info = agent.get_session_info()
    print(f"\n{'='*50}")
    print(f"会话 ID: {info['session_id']}")
    print(f"消息数量: {info['message_count']}")
    print(f"LLM 模型: {info['llm_model']}")
    print(f"LLM 温度: {info['llm_temperature']}")
    print(f"{'='*50}\n")


def interactive_mode():
    """交互模式"""
    print_banner()
    print_help()
    
    # 创建默认会话
    agent = create_session()
    print(f"\n✅ 已创建新会话: {agent.get_session_id()}")
    print(f"💡 输入 'help' 查看可用命令\n")
    
    while True:
        try:
            # 获取用户输入
            user_input = input("🤖 FormAgent > ").strip()
            
            # 处理空输入
            if not user_input:
                continue
            
            # 处理退出命令
            if user_input.lower() in ('quit', 'exit', 'q'):
                print("\n👋 再见！")
                break
            
            # 处理帮助命令
            if user_input.lower() in ('help', 'h', '?'):
                print_help()
                continue
            
            # 处理清空历史命令
            if user_input.lower() == 'clear':
                agent.clear_history()
                print("✅ 已清空当前会话的对话历史")
                continue
            
            # 处理创建新会话命令
            if user_input.lower() == 'new':
                agent = create_session()
                print(f"✅ 已创建新会话: {agent.get_session_id()}")
                continue
            
            # 处理查看会话列表命令
            if user_input.lower() == 'sessions':
                sessions = list_sessions()
                if sessions:
                    print(f"\n📋 所有会话（共 {len(sessions)} 个）：")
                    for i, session in enumerate(sessions, 1):
                        current = " ← 当前" if session['session_id'] == agent.get_session_id() else ""
                        print(f"  {i}. {session['session_id'][:8]}... (消息: {session['message_count']}){current}")
                else:
                    print("\n📋 暂无会话")
                print()
                continue
            
            # 处理切换会话命令
            if user_input.lower().startswith('switch '):
                session_id = user_input[7:].strip()
                agent = create_session(session_id)
                print(f"✅ 已切换到会话: {agent.get_session_id()}")
                continue
            
            # 处理删除会话命令
            if user_input.lower().startswith('delete '):
                session_id = user_input[7:].strip()
                if delete_session(session_id):
                    print(f"✅ 已删除会话: {session_id}")
                    if session_id == agent.get_session_id():
                        agent = create_session()
                        print(f"✅ 已创建新会话: {agent.get_session_id()}")
                else:
                    print(f"❌ 会话不存在: {session_id}")
                continue
            
            # 处理查看会话信息命令
            if user_input.lower() == 'info':
                print_session_info(agent)
                continue
            
            # 处理普通对话
            print(f"\n👤 用户: {user_input}\n")
            response = agent.chat(user_input)
            print(f"🤖 Agent: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {e}\n")
            import traceback
            if '--debug' in sys.argv:
                traceback.print_exc()


def demo_mode():
    """演示模式 - 运行预设示例"""
    print_banner()
    print("\n🎯 演示模式\n")
    
    # 创建会话
    agent = create_session()
    
    # 示例表单结构
    example_schema = json.dumps({
        "fields": [
            {
                "key": "name",
                "name": "姓名",
                "type": "text",
                "required": True
            },
            {
                "key": "age",
                "name": "年龄",
                "type": "number",
                "required": True
            },
            {
                "key": "region",
                "name": "区域",
                "type": "select",
                "options": [
                    {"label": "华东", "value": "cn-hangzhou"},
                    {"label": "华北", "value": "cn-beijing"},
                    {"label": "华南", "value": "cn-shenzhen"}
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
    }, ensure_ascii=False)
    
    # 运行演示对话
    demos = [
        ("帮我加载这个表单结构", example_schema),
        ("查看所有字段", None),
        ("设置姓名为张三", None),
        ("设置年龄为25", None),
        ("把区域设置为杭州", None),
        ("查看所有字段的值", None),
        ("隐藏年龄字段", None),
        ("再次查看所有字段的值", None),
    ]
    
    for i, (question, schema) in enumerate(demos, 1):
        print(f"\n{'='*60}")
        print(f"示例 {i}/{len(demos)}")
        print(f"{'='*60}")
        
        if schema:
            print(f"👤 用户: {question}")
            print(f"📋 表单结构: {schema[:100]}...")
            response = agent.chat(question)
        else:
            print(f"👤 用户: {question}")
            response = agent.chat(question)
        
        print(f"🤖 Agent: {response}")
        
        if i < len(demos):
            input("\n按 Enter 继续...")
    
    print("\n\n✅ 演示完成！")


def main():
    """主函数"""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--demo':
            demo_mode()
        elif sys.argv[1] == '--help':
            print_help()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("使用 --help 查看帮助信息")
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
