from app.ingest.source import Source
from app.ingest.web_fetcher import Collection_action_llm
from fastapi import APIRouter

"""“
TODO
希望能做到自适应采集数据
后续也要支持上传文本作为行情建议的准则
"""

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get('/fetch/finance_data')
async def finance_data():
    # 创建东方财富网数据源
    eastmoney_source = Source(
        # https://finance.eastmoney.com/a/ccjdd_1.html
        source_id="https://finance.eastmoney.com/",
        source_name="东方财富网",
        type="web"
    )

    # 执行数据采集
    collected_data = Collection_action_llm(eastmoney_source)

    # 输出采集结果
    print(f"成功采集到 {len(collected_data)} 条数据:")
    for i, item in enumerate(collected_data, 1):
        print(f"{i}. {item}")


@router.get('/fetch/news_data')
def news_data():
    newsData = Source(
        source_id="https://newsnow.busiyi.world/",
        source_name="热搜榜单",
        type="web"
    )

    # 执行采集热搜榜单


    # 输出采集结构

    print("开始收集今日热搜榜单")