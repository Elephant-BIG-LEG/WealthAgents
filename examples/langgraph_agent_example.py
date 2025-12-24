"""
财富Agent - 智能投研分析平台
LangGraph Agent使用示例
演示如何集成并使用LangGraph版本的Agent系统
"""
import os
import sys
import logging
from typing import Dict, Any

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent.langgraph_agent import LangGraphAgent
from app.agent.langgraph_config import LangGraphConfig, LangGraphNodeFactory, AGENT_TEMPLATES

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def basic_usage_example():
    """
    基础使用示例
    演示如何创建并使用LangGraphAgent处理简单的用户请求
    """
    print("\n=== 基础使用示例 ===")
    
    # 1. 创建LangGraphAgent实例
    try:
        agent = LangGraphAgent()
        print("✅ 成功创建LangGraphAgent实例")
    except Exception as e:
        print(f"❌ 创建LangGraphAgent失败: {str(e)}")
        return
    
    # 2. 处理简单的用户请求
    sample_request = "分析最新的市场趋势和热点投资机会"
    print(f"\n发送请求: {sample_request}")
    
    try:
        response = agent.process_request(sample_request)
        print(f"\n✅ 请求处理完成")
        print(f"状态: {response.get('status', 'unknown')}")
        print(f"结果摘要: {response.get('result_summary', '无摘要')}")
        
        # 输出执行的任务信息
        if 'execution_result' in response:
            tasks_count = len(response['execution_result'].get('tasks_results', []))
            print(f"执行任务数: {tasks_count}")
    except Exception as e:
        print(f"❌ 请求处理失败: {str(e)}")


def custom_config_example():
    """
    自定义配置示例
    演示如何使用LangGraphConfig自定义Agent行为
    """
    print("\n=== 自定义配置示例 ===")
    
    # 1. 创建自定义配置
    config = LangGraphConfig()
    print("✅ 创建自定义配置实例")
    
    # 2. 创建LangGraphAgent实例
    try:
        agent = LangGraphAgent()
        print("✅ 成功创建LangGraphAgent实例")
    except Exception as e:
        print(f"❌ 创建LangGraphAgent失败: {str(e)}")
        return
    
    # 3. 添加自定义处理器
    def custom_plan_preprocess(plan):
        """自定义计划预处理"""
        print(f"🔧 对计划进行自定义预处理，原始任务数: {len(plan)}")
        # 这里可以对计划进行修改，例如添加新任务、修改现有任务等
        return plan
    
    custom_handlers = {
        "plan_preprocess": custom_plan_preprocess,
        # 可以添加更多自定义处理器
    }
    
    # 4. 使用自定义配置处理请求
    sample_request = "分析腾讯和阿里巴巴的最新财报数据"
    print(f"\n发送请求: {sample_request}")
    
    try:
        response = agent.process_request(
            sample_request,
            max_iterations=2,  # 设置最大迭代次数
            custom_handlers=custom_handlers,  # 添加自定义处理器
            debug_mode=True  # 启用调试模式
        )
        print(f"\n✅ 请求处理完成")
        print(f"状态: {response.get('status', 'unknown')}")
        
        # 输出迭代信息
        iterations = response.get('execution_history', [])
        print(f"总迭代次数: {len(iterations)}")
    except Exception as e:
        print(f"❌ 请求处理失败: {str(e)}")


def template_usage_example():
    """
    模板使用示例
    演示如何使用预定义的Agent模板
    """
    print("\n=== 模板使用示例 ===")
    
    # 1. 列出所有可用模板
    print("可用的Agent模板:")
    for template_name, template_info in AGENT_TEMPLATES.items():
        print(f"- {template_name}: {template_info['description']}")
    
    # 2. 创建使用特定模板的LangGraphAgent
    try:
        agent = LangGraphAgent(
            template_name="basic_plan_act_reflect",  # 使用基础模板
            max_iterations=3  # 设置最大迭代次数
        )
        print("\n✅ 成功创建基于模板的LangGraphAgent实例")
    except Exception as e:
        print(f"❌ 创建LangGraphAgent失败: {str(e)}")
        return
    
    # 3. 处理请求
    sample_request = "收集并分析最近一个月的市场风险数据"
    print(f"\n发送请求: {sample_request}")
    
    try:
        response = agent.process_request(sample_request)
        print(f"\n✅ 请求处理完成")
        print(f"状态: {response.get('status', 'unknown')}")
        
        # 输出反思结果
        if 'plan_reflection' in response:
            reflection = response['plan_reflection']
            print(f"计划成功率: {reflection.get('success_rate', 0):.2%}")
            print(f"平均任务执行时间: {reflection.get('avg_execution_time', 0):.2f}秒")
    except Exception as e:
        print(f"❌ 请求处理失败: {str(e)}")


def batch_processing_example():
    """
    批量处理示例
    演示如何使用LangGraphAgent处理多个请求
    """
    print("\n=== 批量处理示例 ===")
    
    # 1. 创建LangGraphAgent实例
    try:
        agent = LangGraphAgent()
        print("✅ 成功创建LangGraphAgent实例")
    except Exception as e:
        print(f"❌ 创建LangGraphAgent失败: {str(e)}")
        return
    
    # 2. 准备多个请求
    batch_requests = [
        "分析新能源板块的投资机会",
        "整理科技股的最新市场表现",
        "总结近期宏观经济数据变化"
    ]
    
    print(f"\n准备处理 {len(batch_requests)} 个请求")
    
    # 3. 逐个处理请求
    results = []
    for i, request in enumerate(batch_requests, 1):
        print(f"\n🔄 处理请求 {i}/{len(batch_requests)}: {request}")
        try:
            response = agent.process_request(request)
            status = response.get('status', 'unknown')
            print(f"   状态: {status}")
            results.append((request, status))
        except Exception as e:
            print(f"   ❌ 失败: {str(e)}")
            results.append((request, 'error'))
    
    # 4. 输出批量处理统计
    print("\n=== 批量处理统计 ===")
    successful = sum(1 for _, status in results if status == 'success')
    failed = sum(1 for _, status in results if status == 'error')
    
    print(f"总请求数: {len(results)}")
    print(f"成功请求: {successful} ({successful/len(results)*100:.1f}%)")
    print(f"失败请求: {failed} ({failed/len(results)*100:.1f}%)")


def integration_example():
    """
    系统集成示例
    演示如何将LangGraphAgent集成到现有系统中
    """
    print("\n=== 系统集成示例 ===")
    
    class WealthAgentService:
        """财富Agent服务封装类"""
        
        def __init__(self):
            """初始化服务"""
            self.agent = LangGraphAgent()
            print("✅ WealthAgentService 初始化完成")
        
        def handle_user_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
            """处理用户请求
            
            Args:
                request_data: 包含用户请求信息的字典
                
            Returns:
                处理结果字典
            """
            # 从请求数据中提取参数
            user_query = request_data.get('query')
            user_id = request_data.get('user_id', 'anonymous')
            session_id = request_data.get('session_id', 'default')
            options = request_data.get('options', {})
            
            print(f"\n🔔 接收来自用户 {user_id} 的请求")
            
            # 使用LangGraphAgent处理请求
            try:
                response = self.agent.process_request(
                    user_query,
                    **options
                )
                
                # 构建标准响应格式
                return {
                    'status': response.get('status', 'unknown'),
                    'data': response,
                    'metadata': {
                        'user_id': user_id,
                        'session_id': session_id,
                        'timestamp': self.agent._get_current_timestamp()
                    }
                }
            except Exception as e:
                print(f"❌ 处理请求失败: {str(e)}")
                return {
                    'status': 'error',
                    'error': str(e),
                    'metadata': {
                        'user_id': user_id,
                        'session_id': session_id
                    }
                }
    
    # 创建服务实例
    service = WealthAgentService()
    
    # 模拟接收请求
    sample_request = {
        'query': '分析医疗健康行业的投资趋势',
        'user_id': 'test_user_001',
        'session_id': 'session_20231020_001',
        'options': {
            'max_iterations': 2,
            'debug_mode': False
        }
    }
    
    # 处理请求
    result = service.handle_user_request(sample_request)
    print(f"\n✅ 服务响应状态: {result['status']}")


def run_all_examples():
    """
    运行所有示例
    """
    print("================================================")
    print("        财富Agent - LangGraph集成使用示例      ")
    print("================================================")
    
    try:
        # 运行各个示例
        basic_usage_example()
        custom_config_example()
        template_usage_example()
        batch_processing_example()
        integration_example()
        
        print("\n================================================")
        print("           ✅ 所有示例运行完成                  ")
        print("================================================")
        
    except KeyboardInterrupt:
        print("\n❌ 示例执行被用户中断")
    except Exception as e:
        print(f"\n❌ 示例执行出错: {str(e)}")


if __name__ == "__main__":
    # 运行示例
    run_all_examples()
