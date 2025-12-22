from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import dotenv
from langchain_openai import ChatOpenAI
import os
dotenv.load_dotenv()

"""
利用大模型总结观点
TODO
Prompt模板、Prompt内容
"""
class LangChainHelperWithSummary:
    def __init__(self, model="qwen-plus"):
        # 初始化模型和提示模板
        self.llm = ChatOpenAI(
            model=model,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        # 创建提示模板，要求将每条新闻内容结构化输出
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "你是一个金融分析师，负责从多篇财经新闻或报告中提取并总结今日市场的热点、趋势、投资建议等关键信息。请确保内容健康合规，避免涉及政治敏感话题和不当内容。"),
            ("user", """
                请根据以下多篇今天的财经新闻或报告，提炼出今日的市场热点，并总结相关的行情趋势和投资建议。

                下面是需要处理的文章内容：

                {articles_content}

                请按照以下格式总结每篇文章的内容，并提炼出今日热点：

                {{
                    "date": "今日日期",
                    "topic": "文章主题",
                    "market_trend": "行情趋势总结",
                    "investment_advice": "投资建议",
                    "hotspot_summary": "今日市场热点总结"
                }}
            """)
        ])

        # 使用Json输出解析器
        self.output_parser = JsonOutputParser()
        # 构建链
        self.chain = self.prompt | self.llm | self.output_parser

    def get_response(self, user_input):
        """
        给定用户输入，返回JSON格式的响应。

        参数：
        - user_input (str/list/dict): 用户输入数据

        返回：
        - dict: JSON格式的解析结果，包括问题和回答
        """
        try:
            # 处理不同类型的输入格式
            if isinstance(user_input, dict) and 'articles_content' in user_input:
                # 如果已经是正确格式的字典，直接使用
                articles_content = user_input['articles_content']
            else:
                # 否则将输入内容作为articles_content参数传递
                articles_content = user_input
                
            # 调用链并获取结果
            result = self.chain.invoke({"articles_content": articles_content})
            return result
        except Exception as e:
            print(f"处理数据时出错: {e}")
            # 返回默认的安全格式数据，避免内容审查问题
            return {
                "date": "",
                "topic": "数据处理异常",
                "market_trend": "",
                "investment_advice": "",
                "hotspot_summary": ""
            }