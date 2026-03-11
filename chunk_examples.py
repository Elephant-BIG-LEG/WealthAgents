"""
递归分块（Recursive Chunking）使用示例
展示新的 Recursive Chunking + Overlap + Metadata 模式
"""

from app.chunk.splitter import (
    FinancialTextSplitter, 
    TextChunk, 
    split_financial_text,
    create_financial_splitter
)


# ============================================
# 示例 1: 基础用法 - 简单递归分割
# ============================================
def example_1_basic_recursive_chunking():
    """基础递归分割示例"""
    
    # 创建切片器实例
    splitter = FinancialTextSplitter(
        chunk_size=600,      # 目标块大小 600 字符
        chunk_overlap=90,    # 重叠 90 字符（15%）
        min_chunk_size=150   # 最小 150 字符
    )
    
    # 长文本
    text = """
    特斯拉 2024 年第三季度财务报告
    
    一、主要财务指标
    
    特斯拉公司（Tesla Inc.）在 2024 年第三季度实现了强劲的财务表现。
    营收达到 233.5 亿美元，同比增长 35%，超出市场预期的 230 亿美元。
    净利润为 50.2 亿美元，较去年同期增长 42%。
    毛利率提升至 25.3%，环比增长 1.2 个百分点。
    
    二、业务板块分析
    
    1. 汽车销售业务
    汽车销售收入为 198.6 亿美元，占总营收的 85%。
    Model Y 和 Model 3 继续贡献主要收入，占比分别为 60% 和 30%。
    平均售价（ASP）为 4.8 万美元，同比下降 5%，主要由于价格调整策略。
    
    2. 能源发电与存储业务
    能源业务收入为 15.6 亿美元，同比增长 40%。
    储能部署量达到 4.0 GWh，创历史新高。
    太阳能部署量为 223 MW，环比增长 15%。
    
    三、生产和交付数据
    
    第三季度产量为 43.5 万辆，同比增长 30%。
    交付量为 43.2 万辆，同比增长 28%。
    上海工厂产能利用率达到 95%，柏林工厂产能持续爬坡。
    
    四、财务状况
    
    截至报告期末，现金及现金等价物为 260 亿美元。
    自由现金流为 32 亿美元，同比增长 55%。
    资产负债率降至 18%，财务结构进一步优化。
    
    五、未来展望
    
    公司预计 2024 年全年交付量将达到 180 万辆，同比增长 35%。
    计划在未来两年内推出两款新车型。
    Cybertruck 量产进度顺利，预计明年 Q2 开始交付。
    """
    
    # 执行递归分割
    chunks = splitter.split_text(text)
    
    print(f"原文本长度：{len(text)} 字符")
    print(f"生成块数：{len(chunks)} 个")
    print(f"平均块大小：{splitter.get_stats()['avg_chunk_size']:.1f} 字符\n")
    
    # 查看第一个块的详细信息
    first_chunk = chunks[0]
    print("=== 第一个文本块 ===")
    print(f"ID: {first_chunk.chunk_id}")
    print(f"长度：{len(first_chunk.text)} 字符")
    print(f"位置：{first_chunk.start_pos} - {first_chunk.end_pos}")
    print(f"元数据：{first_chunk.metadata}")
    print(f"内容预览：{first_chunk.text[:100]}...\n")
    
    # 查看所有块的统计
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}: {len(chunk.text)} 字符 | "
              f"Overlap: {chunk.metadata.get('has_overlap', False)} | "
              f"Merged: {chunk.metadata.get('merge_count', 1)}")


# ============================================
# 示例 2: 添加自定义元数据
# ============================================
def example_2_with_custom_metadata():
    """添加自定义元数据示例"""
    
    splitter = create_financial_splitter()
    
    text = """
    比亚迪股份有限公司 2024 年年度报告摘要
    
    营业收入：6023 亿元，同比增长 42%
    净利润：300 亿元，同比增长 80%
    新能源汽车销量：302 万辆，同比增长 62%
    """
    
    # 添加自定义元数据
    metadata = {
        'source': 'company_annual_report',
        'company_name': '比亚迪',
        'report_year': 2024,
        'file_name': '比亚迪_2024 年报.pdf',
        'document_type': '年度报告'
    }
    
    chunks = splitter.split_text(text, metadata=metadata)
    
    print("\n=== 带元数据的文本块 ===")
    for chunk in chunks:
        print(f"\nChunk ID: {chunk.chunk_id}")
        print(f"来源：{chunk.metadata.get('source')}")
        print(f"公司：{chunk.metadata.get('company_name')}")
        print(f"年份：{chunk.metadata.get('report_year')}")
        print(f"文件：{chunk.metadata.get('file_name')}")
        print(f"索引：{chunk.metadata.get('chunk_index')} / {chunk.metadata.get('total_chunks')}")


# ============================================
# 示例 3: 递归分割层级演示
# ============================================
def example_3_recursive_levels_demo():
    """展示递归分割的层级处理过程"""
    
    splitter = FinancialTextSplitter(
        chunk_size=300,  # 较小的块以便演示
        chunk_overlap=50
    )
    
    # 结构化文本（有明确的章节层次）
    text = """
    # 第一章 公司概况
    
    ## 1.1 基本信息
    
    公司名称：特斯拉股份有限公司
    成立时间：2003 年
    总部地点：美国德克萨斯州
    
    ## 1.2 主营业务
    
    电动汽车研发、生产与销售
    太阳能发电系统
    储能产品和相关服务
    
    # 第二章 财务数据
    
    ## 2.1 营收情况
    
    2024 年 Q3 营收 233.5 亿美元
    同比增长 35%
    环比增长 8%
    
    ## 2.2 利润情况
    
    净利润 50.2 亿美元
    毛利率 25.3%
    净利率 21.5%
    """
    
    chunks = splitter.split_text(text)
    
    print("\n=== 递归分割层级演示 ===")
    print(f"原文本：{len(text)} 字符")
    print(f"分割后：{len(chunks)} 个块\n")
    
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}] 位置：{chunk.start_pos:4d}-{chunk.end_pos:4d} | "
              f"长度：{len(chunk.text):3d} 字符 | "
              f"重叠：{'✓' if chunk.metadata.get('has_overlap') else '✗'}")
        print(f"    内容：{chunk.text[:60].strip()}...")


# ============================================
# 示例 4: 智能重叠效果对比
# ============================================
def example_4_overlap_comparison():
    """对比有无重叠的效果"""
    
    text = """
    特斯拉在上海超级工厂举办了第 100 万辆整车下线仪式。
    这款里程碑式的车辆是一辆 Model Y 长续航版。
    上海工厂从 2019 年开工建设到现在的百万辆下线，仅用了 3 年多时间。
    这创造了全球汽车工厂产能爬坡的新纪录。
    """
    
    # 不加重叠
    splitter_no_overlap = FinancialTextSplitter(
        chunk_size=80,
        chunk_overlap=0,
        add_metadata=False
    )
    chunks_no_overlap = splitter_no_overlap.split_text(text)
    
    # 加重叠
    splitter_with_overlap = FinancialTextSplitter(
        chunk_size=80,
        chunk_overlap=20,
        add_metadata=True
    )
    chunks_with_overlap = splitter_with_overlap.split_text(text)
    
    print("\n=== 无重叠分割 ===")
    for i, chunk in enumerate(chunks_no_overlap, 1):
        print(f"{i}. {chunk.text}")
    
    print("\n=== 有重叠分割 ===")
    for i, chunk in enumerate(chunks_with_overlap, 1):
        overlap_info = f"(重叠{chunk.metadata.get('overlap_size', 0)}字)" if chunk.metadata.get('has_overlap') else ""
        print(f"{i}. {overlap_info} {chunk.text}")
    
    print("\n效果对比：")
    print("- 无重叠：信息被切断，语义不连贯")
    print("- 有重叠：保留了上下文，便于理解")


# ============================================
# 示例 5: 小 chunk 合并效果
# ============================================
def example_5_merge_small_chunks():
    """展示自动合并小 chunk 的功能"""
    
    # 短文本（容易产生碎片化的小 chunk）
    text = """
    特斯拉股价今日上涨 5%。
    分析师看好后市表现。
    目标价上调至 300 美元。
    建议投资者逢低买入。
    """
    
    # 禁用合并（默认行为）
    splitter_no_merge = FinancialTextSplitter(
        chunk_size=100,
        min_chunk_size=50  # 较小的阈值
    )
    
    chunks = splitter_no_merge.split_text(text)
    
    print("\n=== 自动合并小 chunk ===")
    print(f"原文本：{len(text)} 字符")
    print(f"生成块数：{len(chunks)} 个\n")
    
    for chunk in chunks:
        merged_from = chunk.metadata.get('merged_from', [])
        print(f"Chunk: {len(chunk.text)} 字符")
        if len(merged_from) > 1:
            print(f"  ← 由 {len(merged_from)} 个小 chunk 合并而成")
        print(f"  内容：{chunk.text}\n")


# ============================================
# 示例 6: 统计信息追踪
# ============================================
def example_6_statistics_tracking():
    """查看详细的分割统计信息"""
    
    splitter = FinancialTextSplitter(
        chunk_size=400,
        chunk_overlap=60
    )
    
    # 长文本
    text = """
    [此处省略 3000 字的详细财务报告...]
    """ * 3  # 模拟长文本
    
    chunks = splitter.split_text(text)
    stats = splitter.get_stats()
    
    print("\n=== 分割统计信息 ===")
    print(f"总块数：{stats['total_chunks']}")
    print(f"总字符数：{stats['total_characters']}")
    print(f"平均块大小：{stats['avg_chunk_size']:.1f} 字符")
    print(f"空间利用率：{stats['total_characters'] / len(text):.1%}")


# ============================================
# 示例 7: 便捷函数用法
# ============================================
def example_7_convenience_function():
    """使用便捷函数快速分割"""
    
    text = "这是一段测试文本。" * 50
    
    # 使用全局默认配置
    chunks = split_financial_text(text)
    
    # 使用自定义配置
    chunks_custom = split_financial_text(
        text,
        metadata={'source': 'test'},
        chunk_size=200,
        chunk_overlap=30
    )
    
    print("\n=== 便捷函数用法 ===")
    print(f"默认配置：{len(chunks)} 个块")
    print(f"自定义配置：{len(chunks_custom)} 个块")


if __name__ == "__main__":
    print("=" * 60)
    print("Recursive Chunking + Overlap + Metadata 使用示例")
    print("=" * 60)
    
    # 运行示例
    example_1_basic_recursive_chunking()
    # example_2_with_custom_metadata()
    # example_3_recursive_levels_demo()
    # example_4_overlap_comparison()
    # example_5_merge_small_chunks()
    # example_6_statistics_tracking()
    # example_7_convenience_function()
