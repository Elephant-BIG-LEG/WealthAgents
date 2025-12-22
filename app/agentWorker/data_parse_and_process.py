from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import dotenv
from langchain_openai import ChatOpenAI
import os
dotenv.load_dotenv()

""""
利用大模型来处理采集的数据
包括解析、清洗 和 切分数据
TODO
Prompt模板、Prompt内容
"""
class LangChainHelperWithIntegration:
    def __init__(self, model="qwen-plus"):
        # 初始化模型和提示模板
        self.llm = ChatOpenAI(
            model=model,
            base_url=os.getenv("DASHSCOPE_BASE_URL"),
            api_key=os.getenv("DASHSCOPE_API_KEY")
        )
        # 创建提示模板，要求将每条新闻内容结构化输出
        # self.prompt = ChatPromptTemplate.from_messages([
        #     ("system", "你是一个新闻摘要和结构化整理专家。你将根据输入的新闻内容，提取标题、链接和摘要信息。"),
        #     ("user", """
        #         请根据以下新闻内容提取每条新闻的标题、链接、和简要摘要：
        #
        #         1. 标题: 突然！美国发出警告！9家企业被点名！
        #         内容: 科技领域，摩擦不断！在Alphabet旗下谷歌、马斯克旗下媒体平台X、扎克伯格旗下Meta等美国科技巨头接连遭欧盟罚款或调查后，特朗普政府威胁采取报复措施……
        #
        #         2. 标题: 今日复牌！中金收购东兴、信达方案出炉！
        #         内容: 备受市场瞩目的中金公司吸收合并东兴证券、信达证券，迎接重要进展……
        #
        #         3. 标题: 碳纤维巨头官宣涨价 龙头2分钟直线涨停！
        #         内容: A股三大股指早盘走势分化，截至午间收盘，沪指涨0.16%，深成指跌0.85%，创业板指跌1.81%……
        #
        #         4. 标题: 奥普光电秒速涨停！光刻机产业国产化不断提速 受益股曝光（名单）
        #         内容: 光刻机行业进展不断。奥普光电早盘大幅异动，竞价交易后，该股马上被大单推上涨停板……
        #
        #         请按照以下格式输出每条新闻的结构化信息：
        #
        #         {{
        #             "title": "新闻标题",
        #             "summary": "新闻摘要"
        #         }}
        #
        #         下面是需要处理的新闻内容：
        #         {news_content}
        #     """)
        # ])
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "你是一个文本结构化处理工具，只负责对已有文本进行字段提取与重组，不进行任何分析、判断、推测或价值评价，也不新增任何信息。"
            ),
            (
                "user",
                """
        请严格基于输入文本本身，对每条新闻进行结构化整理，仅提取已有信息，不进行改写、不补充、不评价。

        处理规则：
        - 只使用原文中已经出现的文字
        - 不进行背景解释、趋势判断或观点总结
        - 不生成投资建议或立场性描述
        - 如果某字段在原文中不存在，则返回空字符串

        请按以下 JSON 格式输出每条新闻的信息：

        {{
          "title": "原文中的新闻标题",
          "summary": "从原文内容中截取或压缩得到的简要描述（不新增信息）"
        }}

        需要处理的新闻原文如下：
        {news_content}
        """
            )
        ])
        # 使用Json输出解析器
        self.output_parser = JsonOutputParser()
        # 构建链
        self.chain = self.prompt | self.llm | self.output_parser

    def get_response(self, user_input):
        """
        给定用户输入，返回JSON格式的响应。

        参数：
        - user_input (str/list): 用户输入数据

        返回：
        - dict: JSON格式的解析结果，包括问题和回答
        """
        try:
            # 如果输入是列表，将其转换为字符串
            if isinstance(user_input, list):
                # 处理列表格式
                if all(isinstance(item, dict) for item in user_input):
                    # 如果列表中的元素是字典，将其转换为可读字符串
                    formatted_content = "\n\n".join([
                        f"标题: {item.get('title', '无标题')}\n" 
                        f"内容: {item.get('content', item.get('summary', ''))}"
                        for item in user_input
                    ])
                else:
                    # 其他列表格式，简单拼接
                    formatted_content = "\n\n".join(str(item) for item in user_input)
            else:
                # 非列表格式，直接使用
                formatted_content = str(user_input)
            
            # 调用链并获取结果
            result = self.chain.invoke({"news_content": formatted_content})
            return result
        except Exception as e:
            print(f"处理数据时出错: {e}")
            # 返回默认值，确保程序不会中断
            return {"title": "数据处理出错", "link": "", "summary": f"处理数据时出错: {e}"}