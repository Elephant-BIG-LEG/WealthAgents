"""
RAG 增强版检索 - 使用示例

本文件展示如何使用增强版 RAG 检索系统
"""

# ============================================
# 示例 1: 基础使用 - 简单检索
# ============================================
def example_1_basic_search():
    """基础检索示例"""
    from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
    
    # 假设已有 FAISS 向量存储
    from app.store.faiss_store import FaissVectorStore
    vector_store = FaissVectorStore(dimension=768)
    
    # 创建增强版 RAG 检索器
    rag_retriever = EnhancedRAGRetriever(
        vector_store=vector_store,
        enable_hybrid=True,           # 启用混合检索
        enable_query_rewrite=True,    # 启用查询改写
        dense_weight=0.6,             # 向量检索权重
        sparse_weight=0.4             # BM25 权重
    )
    
    # 执行检索
    query = "特斯拉 2024 年财报分析"
    results = rag_retriever.retrieve(
        query=query,
        top_k=5,
        return_context=False  # 返回原始结果列表
    )
    
    # 打印结果
    for text, score, metadata in results:
        print(f"相关度：{score:.3f} | 来源：{metadata.get('source', '未知')}")
        print(f"内容：{text[:100]}...\n")


# ============================================
# 示例 2: 带元数据过滤的检索
# ============================================
def example_2_filtered_search():
    """带过滤条件的检索"""
    from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
    
    # ... 初始化代码同上 ...
    
    rag_retriever = EnhancedRAGRetriever(vector_store=vector_store)
    
    # 执行带过滤的检索
    results = rag_retriever.retrieve_with_metadata_filter(
        query="财务风险分析",
        top_k=5,
        source_filter='web_scraping',  # 只从网络采集数据中检索
        min_similarity=0.5,            # 最小相似度阈值
        date_range=('2024-01-01', '2024-12-31')  # 日期范围
    )
    
    for text, score, metadata in results:
        print(f"相关度：{score:.3f}")
        print(f"内容：{text[:100]}...\n")


# ============================================
# 示例 3: 获取组装后的上下文（用于 LLM 生成）
# ============================================
def example_3_context_assembly():
    """获取组装后的上下文（推荐用于 RAG 场景）"""
    from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
    
    # ... 初始化代码 ...
    
    rag_retriever = EnhancedRAGRetriever(vector_store=vector_store)
    
    query = "某公司的市场竞争力如何？"
    
    # 获取组装后的上下文（直接用于 LLM Prompt）
    context = rag_retriever.retrieve(
        query=query,
        top_k=5,
        return_context=True  # 返回组装后的上下文
    )
    
    print("=== 组装后的上下文 ===")
    print(context)
    print("====================")
    
    # 构造 LLM Prompt
    prompt = f"""
基于以下信息回答问题：

{context}

问题：{query}

请根据以上信息给出详细回答：
"""
    
    # 调用 LLM
    # response = llm.generate(prompt)
    # print(response)


# ============================================
# 示例 4: 查询改写和多查询检索
# ============================================
def example_4_query_expansion():
    """查询改写和扩展示例"""
    from app.retrieval.query_optimizer import QueryRewriter
    
    rewriter = QueryRewriter()
    
    original_query = "新能源车行业风险分析"
    
    # 扩展查询
    expanded_queries = rewriter.expand_query(original_query, num_expansions=3)
    
    print("原始查询:", original_query)
    print("\n扩展查询:")
    for i, q in enumerate(expanded_queries, 1):
        print(f"{i}. {q}")
    
    # 输出示例:
    # 原始查询：新能源车行业风险分析
    # 
    # 扩展查询:
    # 1. 新能源汽车行业风险评估
    # 2. 电动汽车产业风险因素
    # 3. 新能源车市风险挑战


# ============================================
# 示例 5: 混合检索配置（调整权重）
# ============================================
def example_5_hybrid_weights():
    """调整混合检索权重"""
    from app.retrieval.hybrid_retriever import HybridRetriever
    
    # 创建混合检索器
    hybrid_retriever = HybridRetriever(
        vector_store=vector_store,
        bm25_retriever=bm25_retriever,
        vectorizer=vectorizer,
        dense_weight=0.8,  # 提高向量检索权重（更侧重语义）
        sparse_weight=0.2  # 降低 BM25 权重
    )
    
    # 或者反过来（更侧重关键词匹配）
    hybrid_retriever.set_weights(
        dense_weight=0.3,
        sparse_weight=0.7
    )
    
    results = hybrid_retriever.search("特定关键词查询", top_k=5)


# ============================================
# 示例 6: Re-ranking 重排序（精排）
# ============================================
def example_6_reranking():
    """Re-ranking 重排序示例"""
    from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
    
    # 启用 Re-ranking
    rag_retriever = EnhancedRAGRetriever(
        vector_store=vector_store,
        enable_rerank=True  # 启用 Re-ranking
    )
    
    query = "复杂的金融分析问题"
    
    # 执行检索（自动包含 Re-ranking）
    results = rag_retriever.retrieve(
        query=query,
        top_k=5,
        return_context=False
    )
    
    # Re-ranking 后的结果质量更高
    for text, score, metadata in results:
        rerank_score = metadata.get('rerank_score', 'N/A')
        print(f"重排序分数：{rerank_score:.3f} | 原始分数：{score:.3f}")


# ============================================
# 示例 7: 智能上下文组装
# ============================================
def example_7_context_assembler():
    """智能上下文组装示例"""
    from app.retrieval.context_assembler import ContextAssembler
    
    assembler = ContextAssembler(
        max_tokens=1500,              # 控制上下文长度
        similarity_threshold=0.5      # 相似度阈值
    )
    
    # 模拟检索结果
    results = [
        ("高相关性内容 1...", 0.92, {'source': '财报', 'timestamp': '2024-01-15'}),
        ("高相关性内容 2...", 0.88, {'source': '研报', 'timestamp': '2024-02-20'}),
        ("中等相关性内容...", 0.65, {'source': '新闻', 'timestamp': '2024-03-10'}),
        ("低相关性内容...", 0.45, {'source': '论坛', 'timestamp': '2024-04-05'}),
    ]
    
    # 智能组装
    context = assembler.assemble(results, query="某公司财务状况")
    
    print(context)
    # 输出特点：
    # - 高相关性内容：完整保留
    # - 中等相关性：可能摘要
    # - 低相关性：丢弃或简要提及


# ============================================
# 示例 8: 完整的 RAG 流程（推荐实践）
# ============================================
def example_8_complete_rag_pipeline():
    """完整的 RAG 流程示例"""
    from app.retrieval.enhanced_rag_retriever import EnhancedRAGRetriever
    
    # 1. 初始化检索器
    rag_retriever = EnhancedRAGRetriever(
        vector_store=vector_store,
        model_name='shibing624/text2vec-base-chinese',
        enable_hybrid=True,
        enable_rerank=True,
        enable_query_rewrite=True,
        dense_weight=0.6,
        sparse_weight=0.4
    )
    
    # 2. 用户查询
    user_query = "请分析特斯拉的财务风险和市场竞争地位"
    
    # 3. 执行检索
    context = rag_retriever.retrieve(
        query=user_query,
        top_k=7,
        return_context=True,
        filters={
            'min_similarity': 0.4,
            'source': ['财报', '研报', '权威媒体']
        }
    )
    
    # 4. 构造 Prompt
    prompt = f"""
你是一个专业的金融分析师。请基于以下信息回答问题。

【相关信息】
{context}

【问题】
{user_query}

【要求】
1. 回答要准确、专业、有深度
2. 引用信息来源
3. 如有不确定，请说明
4. 使用中文回答

【回答】
"""
    
    # 5. 调用 LLM 生成回答
    # response = llm.generate(prompt)
    # return response


# ============================================
# 示例 9: 性能优化 - 缓存和批量处理
# ============================================
def example_9_performance_optimization():
    """性能优化示例"""
    from app.Embedding.sbert_vectorization import SBertVectorizer
    
    # 启用缓存
    vectorizer = SBertVectorizer(
        model_name='shibing624/text2vec-base-chinese',
        cache_enabled=True  # 启用缓存
    )
    
    # 批量向量化（比单个处理快）
    texts = ["文本 1", "文本 2", "文本 3", ...]  # 大量文本
    
    vectors = vectorizer.vectorize_texts(
        texts,
        batch_size=32,          # 批次大小
        show_progress=True      # 显示进度条
    )
    
    # 首次处理后，相同文本会直接从缓存读取
    cached_vector = vectorizer.vectorize_text("文本 1")  # 秒级响应


# ============================================
# 示例 10: 自定义配置和高级用法
# ============================================
def example_10_advanced_usage():
    """高级配置示例"""
    from app.retrieval.bm25_retriever import BM25Retriever
    
    # 自定义 BM25 参数
    bm25 = BM25Retriever(
        k1=1.2,  # 词频饱和度（降低使 TF 更线性）
        b=0.8    # 长度归一化（提高对长文档的惩罚）
    )
    
    # 添加文档
    documents = [(1, "文档 1 内容"), (2, "文档 2 内容"), ...]
    bm25.add_documents(documents)
    
    # 搜索
    results = bm25.search("查询词", top_k=10)
    
    # 自定义 RRF 参数
    from app.retrieval.hybrid_retriever import HybridRetriever
    
    hybrid = HybridRetriever(
        k=40  # RRF 融合参数（越小越看重排名）
    )


if __name__ == "__main__":
    print("=" * 60)
    print("RAG 增强版检索 - 使用示例集合")
    print("=" * 60)
    
    # 运行示例
    # example_1_basic_search()
    # example_2_filtered_search()
    # example_3_context_assembly()
    # ...
