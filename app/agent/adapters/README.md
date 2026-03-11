"""
财富 Agent - 智能投研分析平台
Adapter 层使用指南

本文档介绍如何使用 Adapter 层的各种适配器
"""

# ============================================================
# 1. 快速开始
# ============================================================

## 1.1 导入适配器

```python
from app.agent.adapters.market_data_adapter import MarketDataAdapter
from app.agent.adapters.financial_report_adapter import FinancialReportAdapter
from app.agent.adapters.risk_assessment_adapter import RiskAssessmentAdapter
from app.agent.adapters.external_api_adapter import ExternalAPIAdapter
```

## 1.2 基本使用模式

所有适配器都遵循统一的使用模式：
1. 创建适配器实例
2. 连接到数据源
3. 获取数据
4. 转换数据为标准格式
5. 断开连接（可选）


# ============================================================
# 2. 行情数据适配器使用示例
# ============================================================

## 2.1 获取实时行情

```python
from app.agent.adapters.market_data_adapter import MarketDataAdapter

# 创建适配器
adapter = MarketDataAdapter()

# 连接到新浪数据源
if adapter.connect(source='sina'):
    print("✓ 连接成功")
    
    # 获取贵州茅台的实时行情
    raw_data = adapter.fetch_data('600519')
    
    # 转换为标准格式
    result = adapter.transform_data(raw_data)
    
    if result['status'] == 'success':
        data = result['data']
        print(f"股票名称：{data['name']}")
        print(f"当前价格：{data['current_price']}")
        print(f"涨跌幅：{data['change_percent']}%")
    
    # 断开连接
    adapter.disconnect()
else:
    print("✗ 连接失败")
```

## 2.2 切换数据源

```python
adapter = MarketDataAdapter()

# 可以切换到其他数据源
adapter.connect(source='eastmoney')
data1 = adapter.fetch_data('000858')

adapter.disconnect()
adapter.connect(source='qq')
data2 = adapter.fetch_data('000858')
```

## 2.3 错误处理

```python
try:
    adapter = MarketDataAdapter()
    adapter.connect()
    
    result = adapter.fetch_data('invalid_symbol')
    transformed = adapter.transform_data(result)
    
    if transformed['status'] == 'error':
        print(f"错误：{transformed['message']}")
        
except Exception as e:
    print(f"异常：{str(e)}")
finally:
    adapter.disconnect()
```


# ============================================================
# 3. 财报数据适配器使用示例
# ============================================================

## 3.1 获取年度财报

```python
from app.agent.adapters.financial_report_adapter import FinancialReportAdapter

adapter = FinancialReportAdapter()

# 连接到东方财富
if adapter.connect(source='eastmoney'):
    # 获取贵州茅台 2023 年年报
    raw_data = adapter.fetch_data(
        query='600519',
        year=2023,
        report_type='annual'
    )
    
    # 转换为标准格式
    result = adapter.transform_data(raw_data)
    
    if result['status'] == 'success':
        data = result['data']
        print(f"公司名称：{data['company_name']}")
        print(f"营业收入：{data['revenue']}元")
        print(f"净利润：{data['net_profit']}元")
        print(f"毛利率：{data['gross_margin']*100}%")
        print(f"ROE: {data['roe']*100}%")
        
        # 检查数据完整性
        completeness = result['metadata']['data_completeness']
        print(f"数据完整性：{completeness*100}%")
    
    adapter.disconnect()
```

## 3.2 获取季度报告

```python
# 获取第一季度财报
raw_data = adapter.fetch_data(
    query='000858',
    year=2024,
    report_type='quarterly',
    quarter=1
)
```


# ============================================================
# 4. 风险评估适配器使用示例
# ============================================================

## 4.1 计算综合风险指标

```python
from app.agent.adapters.risk_assessment_adapter import RiskAssessmentAdapter

adapter = RiskAssessmentAdapter()
adapter.connect()

# 计算多个风险指标
raw_data = adapter.fetch_data(
    query='600519',
    metrics=['volatility', 'var', 'max_drawdown', 'beta', 'sharpe_ratio'],
    period=252,
    confidence_level=0.95
)

# 转换为标准格式
result = adapter.transform_data(raw_data)

if result['status'] == 'success':
    data = result['data']
    print(f"波动率：{data['volatility']*100}%")
    print(f"VaR(95%): {data['var_95']*100}%")
    print(f"最大回撤：{data['max_drawdown']*100}%")
    print(f"Beta 系数：{data['beta']}")
    print(f"夏普比率：{data['sharpe_ratio']}")
    print(f"风险等级：{data['risk_level']}")
    print(f"风险评分：{data['risk_score']}")
```

## 4.2 风险评估报告

```python
def generate_risk_report(symbol: str):
    """生成风险评估报告"""
    adapter = RiskAssessmentAdapter()
    adapter.connect()
    
    raw_data = adapter.fetch_data(
        query=symbol,
        metrics=['volatility', 'var', 'max_drawdown']
    )
    
    result = adapter.transform_data(raw_data)
    
    if result['status'] == 'success':
        data = result['data']
        
        report = f"""
        === {symbol} 风险评估报告 ===
        
        评估时间：{data['assessment_time']}
        
        风险指标:
        - 年化波动率：{data['volatility']*100:.2f}%
        - VaR(95%): {data['var_95']*100:.2f}%
        - 最大回撤：{data['max_drawdown']*100:.2f}%
        - Beta 系数：{data['beta']:.2f}
        - 夏普比率：{data['sharpe_ratio']:.2f}
        
        综合评估:
        - 风险等级：{data['risk_level']}
        - 风险评分：{data['risk_score']:.1f}/100
        
        数据来源：{data['data_source']}
        """
        
        return report
    
    return "评估失败"

# 使用
report = generate_risk_report('600519')
print(report)
```


# ============================================================
# 5. 外部 API 适配器使用示例
# ============================================================

## 5.1 连接 Wind 资讯

```python
from app.agent.adapters.external_api_adapter import ExternalAPIAdapter

adapter = ExternalAPIAdapter()

# 连接到 Wind API
if adapter.connect(
    provider='wind',
    api_key='your_wind_api_key'
):
    print("✓ 已连接到 Wind 资讯")
    
    # 获取行情数据
    market_data = adapter.fetch_data(
        query='600519.SH',
        api_type='market'
    )
    
    # 获取财务数据
    financial_data = adapter.fetch_data(
        query='600519',
        api_type='financial',
        year=2023
    )
    
    adapter.disconnect()
```

## 5.2 连接同花顺

```python
adapter = ExternalAPIAdapter()

adapter.connect(
    provider='ths',
    api_key='your_ths_token'
)

# 获取新闻数据
news_data = adapter.fetch_data(
    query='人工智能',
    api_type='news',
    limit=10
)
```

## 5.3 速率限制处理

```python
import time

adapter = ExternalAPIAdapter()
adapter.connect(provider='datayes', api_key='your_key')

symbols = ['600519', '000858', '000001', '600036']

for symbol in symbols:
    # 适配器会自动检查速率限制
    data = adapter.fetch_data(query=symbol, api_type='market')
    
    if 'error' in data and 'Rate limit' in data['error']:
        print("超过速率限制，等待...")
        time.sleep(60)  # 等待 1 分钟
    
    # 建议主动延时
    time.sleep(1)
```


# ============================================================
# 6. 高级用法
# ============================================================

## 6.1 批量获取数据

```python
def batch_fetch_market_data(symbols: list, source: str = 'sina'):
    """批量获取行情数据"""
    adapter = MarketDataAdapter()
    adapter.connect(source=source)
    
    results = {}
    for symbol in symbols:
        raw_data = adapter.fetch_data(symbol)
        standard_data = adapter.transform_data(raw_data)
        
        if standard_data['status'] == 'success':
            results[symbol] = standard_data['data']
        else:
            results[symbol] = {'error': standard_data.get('message')}
    
    adapter.disconnect()
    return results

# 使用
symbols = ['600519', '000858', '000001', '600036']
all_data = batch_fetch_market_data(symbols)

for symbol, data in all_data.items():
    if 'error' not in data:
        print(f"{symbol}: {data['name']} - {data['current_price']}元")
```

## 6.2 多数据源对比

```python
def compare_data_sources(symbol: str):
    """对比不同数据源的数据质量"""
    sources = ['sina', 'eastmoney', 'qq']
    results = {}
    
    for source in sources:
        adapter = MarketDataAdapter()
        if adapter.connect(source=source):
            raw_data = adapter.fetch_data(symbol)
            standard_data = adapter.transform_data(raw_data)
            
            if standard_data['status'] == 'success':
                results[source] = {
                    'price': standard_data['data']['current_price'],
                    'time': standard_data['data']['timestamp'],
                    'metadata': standard_data['metadata']
                }
            
            adapter.disconnect()
    
    return results

# 使用
comparison = compare_data_sources('600519')
for source, data in comparison.items():
    print(f"{source}: {data['price']}元 @ {data['time']}")
```

## 6.3 数据验证

```python
def validate_and_fetch(adapter, query: str, **params):
    """带验证的数据获取"""
    try:
        # 1. 验证连接
        if not adapter.validate_connection():
            print("连接无效，尝试重连...")
            adapter.connect()
        
        # 2. 检查适配器状态
        status = adapter.get_status()
        print(f"适配器状态：{status}")
        
        # 3. 获取数据
        raw_data = adapter.fetch_data(query, **params)
        
        # 4. 验证数据
        if not raw_data or 'error' in raw_data:
            print(f"数据获取失败：{raw_data.get('error', '未知错误')}")
            return None
        
        # 5. 转换格式
        result = adapter.transform_data(raw_data)
        
        # 6. 验证结果
        if result['status'] == 'success':
            print(f"✓ 成功获取并转换数据")
            return result['data']
        else:
            print(f"✗ 数据转换失败：{result.get('message')}")
            return None
            
    except Exception as e:
        print(f"异常：{str(e)}")
        return None
```


# ============================================================
# 7. 最佳实践
# ============================================================

## 7.1 资源管理

- ✅ 使用上下文管理器确保资源释放
- ✅ 及时调用 disconnect() 断开连接
- ✅ 避免频繁创建和销毁适配器实例

```python
from contextlib import contextmanager

@contextmanager
def adapter_context(adapter):
    """适配器上下文管理器"""
    try:
        adapter.connect()
        yield adapter
    finally:
        adapter.disconnect()

# 使用
with adapter_context(MarketDataAdapter()) as adapter:
    data = adapter.fetch_data('600519')
    # 自动断开连接
```

## 7.2 错误处理

- ✅ 总是检查返回状态
- ✅ 提供有意义的错误信息
- ✅ 实现重试机制

```python
def robust_fetch(adapter, query: str, max_retries: int = 3):
    """健壮的数据获取"""
    for attempt in range(max_retries):
        try:
            raw_data = adapter.fetch_data(query)
            result = adapter.transform_data(raw_data)
            
            if result['status'] == 'success':
                return result['data']
            
            print(f"尝试 {attempt+1}/{max_retries} 失败")
            
        except Exception as e:
            print(f"异常：{str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避
    
    return None
```

## 7.3 性能优化

- ✅ 复用适配器实例
- ✅ 批量获取数据
- ✅ 合理设置超时时间


# ============================================================
# 8. 常见问题
# ============================================================

Q1: 如何选择合适的适配器？
A1: 
- 行情数据 → MarketDataAdapter
- 财报数据 → FinancialReportAdapter
- 风险评估 → RiskAssessmentAdapter
- 第三方 API → ExternalAPIAdapter

Q2: 如何处理 API 密钥？
A2: 从环境变量或配置文件读取，不要硬编码在代码中。

Q3: 如何提高数据获取速度？
A3: 使用批量获取、并行请求、缓存等机制。

Q4: 如何扩展新的数据源？
A4: 继承 BaseToolAdapter，实现抽象方法即可。


# ============================================================
# 9. 相关文件
# ============================================================

- `__init__.py` - 基类定义
- `market_data_adapter.py` - 行情数据适配器
- `financial_report_adapter.py` - 财报数据适配器
- `risk_assessment_adapter.py` - 风险评估适配器
- `external_api_adapter.py` - 外部 API 适配器
