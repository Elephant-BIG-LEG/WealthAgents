# WealthAgents使用示例文档

## LangGraphAgent 使用指南

本文档介绍如何使用基于LangGraph的智能投研Agent组件 - LangGraphAgent。

## 1. 基本导入

```python
from app.agent import LangGraphAgent
from app.agent import MemoryManager
from app.agent import LangGraphConfig
from app.agent import AGENT_TEMPLATES
```

## 2. 初始化LangGraphAgent

### 2.1 基本初始化

```python
# 创建一个基本的LangGraphAgent实例
agent = LangGraphAgent()
```

### 2.2 自定义配置初始化

```python
# 创建带有自定义配置的LangGraphAgent实例
config = {
    "max_iterations": 5,        # 最大迭代次数
    "enable_memory": True,      # 启用记忆功能
    "debug": True               # 启用调试日志
}

agent = LangGraphAgent(config=config, template="basic")
```

### 2.3 使用不同模板

```python
# 使用迭代改进模板
agent = LangGraphAgent(template="iterative_improvement")

# 使用深度分析模板
agent = LangGraphAgent(template="deep_analysis")
```

## 3. 处理请求

### 3.1 基本文本请求

```python
# 处理简单的文本请求
result = agent.process_request("分析最近一周的A股市场行情")
print(f"处理结果: {result}")
```

### 3.2 带上下文的复杂请求

```python
# 处理包含更多上下文信息的请求
complex_request = {
    "user_query": "分析科技股投资机会",
    "context": "用户是一名风险偏好中等的投资者，关注长期价值投资",
    "user_profile": {
        "risk_level": "medium",
        "investment_horizon": "long_term"
    }
}

result = agent.process_request(complex_request)
print(f"处理结果: {result}")
```

## 4. 使用自定义处理函数

```python
# 定义自定义处理函数
def custom_plan_processor(plan):
    """自定义计划处理器"""
    # 添加自定义逻辑
    return plan

def custom_result_formatter(result):
    """自定义结果格式化器"""
    # 添加格式化逻辑
    return result

# 配置自定义处理函数
config = {
    "custom_handlers": {
        "plan_preprocess": custom_plan_processor,
        "result_formatter": custom_result_formatter
    }
}

agent = LangGraphAgent(config=config)
```

## 5. 使用MemoryManager功能

```python
# 启用记忆功能的Agent
config = {"enable_memory": True}
agent = LangGraphAgent(config=config)

# 连续对话示例
result1 = agent.process_request("分析阿里巴巴的基本面")
result2 = agent.process_request("继续分析其技术面")  # 能够基于历史对话提供上下文相关的回复
```

## 6. 错误处理

```python
try:
    agent = LangGraphAgent()
    result = agent.process_request("分析市场趋势")
    print(f"成功: {result}")
except Exception as e:
    print(f"发生错误: {str(e)}")
```

## 7. 使用LangGraphConfig自定义Agent行为

```python
# 创建自定义配置
custom_config = LangGraphConfig()
custom_config.add_node("custom_node", lambda state: state)
custom_config.add_edge("plan", "custom_node")

# 使用自定义配置创建Agent
# 注意：LangGraphConfig的完整使用方法请参考相关文档
```

## 8. 可用的Agent模板

```python
# 查看所有可用的模板
print(AGENT_TEMPLATES.keys())
# 输出: dict_keys(['basic', 'iterative_improvement', 'deep_analysis'])

# 查看特定模板的配置
print(AGENT_TEMPLATES["iterative_improvement"])
```

## 注意事项

1. **LangGraph依赖**：确保已安装langgraph包以获得完整功能
2. **Redis连接**：使用Memory功能时需要确保Redis服务可用
3. **性能优化**：对于大规模应用，考虑调整max_iterations参数以平衡性能和质量
4. **日志级别**：设置debug=True可以查看更详细的执行日志

---

更多高级功能和配置选项请参考完整文档。