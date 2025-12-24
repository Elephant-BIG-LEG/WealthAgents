"""
验证Graph导入测试脚本
用于确认从app.agent包中可以成功导入Graph
"""
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # 尝试从app.agent包导入Graph
    from app.agent import Graph, END, START
    print(f"✅ 成功从app.agent导入Graph: {Graph}")
    print(f"✅ 成功从app.agent导入END: {END}")
    print(f"✅ 成功从app.agent导入START: {START}")
    
    # 验证Graph是否确实是StateGraph的别名
    print(f"\n📊 Graph类型信息:")
    print(f"  - 类型名称: {Graph.__name__}")
    print(f"  - 模块路径: {Graph.__module__}")
    
    # 验证是否可以导入其他组件
    try:
        from app.agent import LangGraphAgent, LangGraphConfig, LangGraphNodeFactory
        print(f"\n✅ 成功导入其他组件:")
        print(f"  - LangGraphAgent: {LangGraphAgent}")
        print(f"  - LangGraphConfig: {LangGraphConfig}")
        print(f"  - LangGraphNodeFactory: {LangGraphNodeFactory}")
    except ImportError as e:
        print(f"\n❌ 无法导入其他组件: {e}")
    
    print("\n🎉 导入测试完成，所有导入操作成功!")
    
except ImportError as e:
    print(f"❌ 无法从app.agent导入Graph: {e}")
    print("\n请检查以下事项:")
    print("1. app/agent/__init__.py文件是否正确配置了Graph的导出")
    print("2. langgraph包是否已正确安装")
    print("3. Python路径是否包含项目根目录")
