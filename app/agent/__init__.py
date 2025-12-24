"""
WealthAgents - Agent 模块初始化文件
"""

import logging

# 定义日志记录器
logger = logging.getLogger(__name__)

# 尝试导入LangGraph相关组件
# 注意：即使langgraph包未安装，也需要保持代码结构完整性
try:
    # 尝试导入langgraph组件
    from langgraph.graph import StateGraph as Graph, END, START
    
    # 标记langgraph组件是否可用
    LANGGRAPH_AVAILABLE = True
    logger.info("LangGraph组件导入成功")
except ImportError:
    # 如果langgraph不可用，创建占位符以保持接口一致性
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph组件不可用，将使用占位符")
    
    # 创建占位符类和常量
    class GraphPlaceholder:
        """Graph占位符类，当langgraph不可用时使用"""
        def __init__(self, *args, **kwargs):
            logger.warning("使用Graph占位符，langgraph包未安装")
    
    Graph = GraphPlaceholder
    END = None
    START = None

# 从子模块导入其他组件
try:
    from .langgraph_agent import LangGraphAgent
    from .langgraph_config import LangGraphConfig, LangGraphNodeFactory, AGENT_TEMPLATES
except ImportError as e:
    logger.warning(f"LangGraph相关模块导入失败: {e}")
    # 创建占位符类以保持接口一致性
    class LangGraphAgentPlaceholder:
        def __init__(self, *args, **kwargs):
            logger.warning("使用LangGraphAgent占位符")
    
    class LangGraphConfigPlaceholder:
        def __init__(self, *args, **kwargs):
            logger.warning("使用LangGraphConfig占位符")
    
    class LangGraphNodeFactoryPlaceholder:
        pass
    
    LangGraphAgent = LangGraphAgentPlaceholder
    LangGraphConfig = LangGraphConfigPlaceholder
    LangGraphNodeFactory = LangGraphNodeFactoryPlaceholder
    AGENT_TEMPLATES = {}

# 定义模块公共接口
__all__ = [
    "LangGraphAgent",
    "LangGraphConfig",
    "LangGraphNodeFactory",
    "AGENT_TEMPLATES",
    "Graph",  # 导出Graph别名
    "END",
    "START",
    "LANGGRAPH_AVAILABLE"  # 添加可用性标记
]

# 从其他模块导入剩余组件
try:
    from .executor import Executor
    from .memory import MemoryManager as Memory  # 修改为导入MemoryManager并使用别名Memory
    from .planner import Planner
    from .private_agent import PrivateAgent
    from .reflector import Reflector
    
    # 将其他组件添加到公共接口
    __all__.extend([
        "Executor",
        "Memory",  # 保持向后兼容，继续使用Memory名称
        "MemoryManager",  # 同时导出MemoryManager以提供明确的名称
        "Planner",
        "PrivateAgent",
        "Reflector"
    ])
    
    # 额外导出MemoryManager以确保完全兼容
    MemoryManager = Memory
except ImportError as e:
    logger.warning(f"部分Agent组件导入失败: {e}")
    
    # 尝试单独导入MemoryManager作为备用
    try:
        from .memory import MemoryManager
        Memory = MemoryManager  # 创建别名以保持向后兼容
        __all__.extend(["Memory", "MemoryManager"])
    except ImportError:
        logger.error("无法从memory模块导入Memory或MemoryManager")
