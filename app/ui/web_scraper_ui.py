import streamlit as st
from app.ingest.source import Source
from app.ingest.web_fetcher import Collection_action_llm

""""
TODO
可视化有很大问题
"""

# 设置页面配置
st.set_page_config(
    page_title="财富代理数据采集系统",
    page_icon="💰",
    layout="wide"
)

# 页面标题
st.title("💰 财富代理数据采集系统")
st.markdown("---")

# 侧边栏配置
st.sidebar.header("数据源配置")

# 数据源选择
data_source = st.sidebar.selectbox(
    "选择数据源",
    ["东方财富网", "自定义网址"]
)

# 根据选择显示不同的输入选项
if data_source == "东方财富网":
    source_url = "https://finance.eastmoney.com/"
    source_name = "东方财富网"
else:
    source_url = st.sidebar.text_input(
        "请输入网址", placeholder="https://example.com")
    source_name = st.sidebar.text_input("数据源名称", placeholder="自定义数据源")

# 采集按钮
collect_button = st.sidebar.button("开始采集数据")

# 主内容区域
col1, col2 = st.columns([2, 1])

with col1:
    st.header("采集结果")

    # 结果显示区域
    if "collected_data" not in st.session_state:
        st.session_state.collected_data = []

    if collect_button:
        if data_source == "自定义网址" and (not source_url or not source_name):
            st.error("请填写完整的网址和数据源名称")
        else:
            # 显示加载状态
            with st.spinner("正在采集数据..."):
                # 创建数据源对象
                source = Source(
                    source_id=source_url,
                    source_name=source_name,
                    type="web"
                )

                # 执行数据采集
                collected_data = Collection_action_llm(source)
                st.session_state.collected_data = collected_data

            st.success(
                f"数据采集完成！共采集到 {len(st.session_state.collected_data)} 条数据")

    # 显示采集结果
    if st.session_state.collected_data:
        st.subheader(f"采集到的数据 ({len(st.session_state.collected_data)} 条)")

        # 显示数据列表
        for i, item in enumerate(st.session_state.collected_data, 1):
            st.write(f"{i}. {item}")
    else:
        st.info("请点击侧边栏的'开始采集数据'按钮来获取数据")

with col2:
    st.header("系统信息")

    # 显示数据源信息
    st.subheader("当前数据源")
    if data_source == "东方财富网":
        st.write(f"**名称**: 东方财富网")
        st.write(f"**网址**: https://finance.eastmoney.com/a/ccjdd.html")
    else:
        st.write(f"**名称**: {source_name or '未设置'}")
        st.write(f"**网址**: {source_url or '未设置'}")

    st.markdown("---")

    # 显示采集统计
    st.subheader("采集统计")
    st.write(f"已采集数据条数: {len(st.session_state.collected_data)}")

    # 清空数据按钮
    if st.button("清空采集结果"):
        st.session_state.collected_data = []
        st.experimental_rerun()

# 页脚
st.markdown("---")
st.caption("财富代理数据采集系统 v1.0")
