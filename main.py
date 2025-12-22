import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def main():
    print("财富代理数据采集系统")
    print("1. 命令行模式")
    print("2. Web界面模式 (Flask)")
    print("3. 向量化测试模式")
    print("4. Faiss向量数据库测试模式")

    choice = input("请选择运行模式 (1, 2, 3 或 4): ").strip()

    if choice == "1":
        # 命令行模式
        from app.ingest.source import Source
        from app.ingest.web_fetcher import Collection_action_llm

        # 创建东方财富网数据源
        eastmoney_source = Source(
            source_id="https://finance.eastmoney.com/",
            source_name="东方财富网",
            type="web"
        )

        print("开始采集东方财富网数据...")

        # 执行数据采集
        collected_data = Collection_action_llm(eastmoney_source)

        # 输出采集结果
        print(f"成功采集到 {len(collected_data)} 条数据:")
        for i, item in enumerate(collected_data, 1):
            print(f"{i}. {item}")

    elif choice == "2":
        # Web界面模式
        print("启动Flask Web界面...")
        os.system("D:\\MinConda\\python.exe -m app.ui.web_app")

    elif choice == "3":
        # 向量化测试模式
        print("向量化功能测试...")
        from app.Embedding.Vectorization import TextVectorizer

        # 创建测试数据
        test_texts = [
            "人工智能是计算机科学的一个分支",
            "机器学习是人工智能的核心技术",
            "深度学习在图像识别领域表现优异",
            "自然语言处理让计算机理解人类语言",
            "数据挖掘从大量数据中发现有价值的信息"
        ]

        # 创建向量化器
        vectorizer = TextVectorizer(vector_dim=64)

        # 向量化文本
        print("正在向量化文本...")
        vectors = vectorizer.vectorize_texts(test_texts)

        # 显示结果
        print(f"\n成功向量化 {len(vectors)} 条文本:")
        for i, (text, vector) in enumerate(zip(test_texts, vectors)):
            print(f"{i+1}. 文本: {text}")
            print(f"   向量维度: {vector.shape}")
            print(f"   向量前5维: {vector[:5]}")
            print()

        # 测试相似度计算
        print("测试文本相似度计算:")
        query = "人工智能技术发展迅速"
        similar_texts = vectorizer.find_similar_texts(
            query, test_texts, top_k=3)

        print(f"查询文本: {query}")
        print("最相似的文本:")
        for i, (text, similarity, index) in enumerate(similar_texts):
            print(f"{i+1}. {text} (相似度: {similarity:.4f})")

    elif choice == "4":
        # Faiss向量数据库测试模式
        print("Faiss向量数据库测试...")
        os.system("D:\\MinConda\\python.exe test_faiss.py")

    else:
        print("无效的选择，请运行程序并输入 1, 2, 3 或 4")


if __name__ == '__main__':
    main()
