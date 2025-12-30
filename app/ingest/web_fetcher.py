from langchain_openai import ChatOpenAI
from app.parse.parsing import parse_data
import requests
import re
from html.parser import HTMLParser
from typing import List, Dict, Any, Union
from app.config.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
from app.ingest.source import Source
from langchain_core.prompts import ChatPromptTemplate
import time
import random
from urllib.parse import urlparse, urljoin
import datetime

"""
TODO
不能采集时自动翻页，只能单页提取
采集数据出现问题了
Agent没有抽出来
"""

# TODO 创建文本提取Agent


def creat_llm(model="qwen-plus"):
    return ChatOpenAI(
        model=model,
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_BASE_URL,
        # TODO 看官方配置修改
        temperature=0
    )


# 创建大模型实例
llm = creat_llm()

# TODO 文本提取Prompt模板
prompt = ChatPromptTemplate.from_messages([
    ("system",
     "你是一个信息提取专家，专门帮助从原始文本中提取有用信息并将其结构化。"
     "请将提取的信息以Python列表的形式返回，每个元素是一条独立的信息。只返回Python列表，不要包含其他内容。例如：['信息1', '信息2', '信息3']"),
    ("user",
     "以下是需要提取和过滤的信息：\n{input}\n请从中提取出有效信息，过滤掉无关的内容，并以Python列表的形式返回。")
])


# 执行采集动作
def Collection_action_llm(source: Source) -> List[Dict[str, Any]]:
    """
    从不同类型的数据源收集信息 - 增强版
    :param source: 数据源对象，包含source_id, source_name, type, url, config等信息
    :return: 收集到的数据列表
    """
    results = []
    try:
        print(f"开始从数据源 {source.source_id} 收集信息...")
        
        # 检查数据源类型
        if source.type == "web":
            print(f"正在调用fetch_financeWeb_data获取数据，URL: {source.url}")
            # 调用网页数据获取函数
            results = fetch_financeWeb_data(source.url)
            print(f"fetch_financeWeb_data返回了 {len(results)} 条结果")
        elif source.type == "news":
            print(f"正在调用fetch_newsWeb_data获取数据，URL: {source.url}")
            # 调用新闻数据获取函数
            results = fetch_newsWeb_data(source.url)
            print(f"fetch_newsWeb_data返回了 {len(results)} 条结果")
        elif source.type == "api":
            print(f"API类型数据源暂不支持: {source.source_id}")
        else:
            print(f"未知数据源类型: {source.type} for {source.source_id}")

        # 数据有效性检查
        if not results:
            print(f"从数据源 {source.source_id} 未获取到有效数据")
            # 尝试使用其他方式获取数据
            if source.type == "web":
                print(f"尝试使用fetch_article_content_simple直接获取内容...")
                try:
                    content = fetch_article_content_simple(source.url)
                    if content:
                        results.append({
                            "title": "直接获取的页面内容",
                            "url": source.url,
                            "content": content,
                            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        print("直接获取内容成功")
                    else:
                        print("直接获取内容失败")
                except Exception as e:
                    print(f"直接获取内容时出错: {e}")
                    import traceback
                    traceback.print_exc()
    except Exception as e:
        print(f"从数据源 {source.source_id} 收集信息时出错: {e}")
        import traceback
        traceback.print_exc()

    return results


class TitleExtractor(HTMLParser):
    """提取HTML中的标题标签内容"""

    def __init__(self):
        super().__init__()
        self.titles = []
        self.in_title_tag = False

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'title':
            self.in_title_tag = True

    def handle_endtag(self, tag):
        if tag.lower() == 'title':
            self.in_title_tag = False

    def handle_data(self, data):
        if self.in_title_tag:
            self.titles.append(data.strip())

# 财经网站采集 - 增强版本

def fetch_financeWeb_data(source: Union[Source, str]) -> List[Dict[str, Any]]:
    """
    采集财经网站数据（增强版 - 支持自动翻页和文章内容获取）
    :param source: 数据源对象或URL字符串
    :return: 采集到的数据列表
    """
    try:
        # 处理source参数，支持Source对象和字符串URL
        if isinstance(source, Source):
            source_id = source.source_id
            # 优先使用source.url，如果为空则使用source.source_id (兼容旧代码逻辑)
            current_url = source.url if source.url else source.source_id
            print(f"开始采集数据源: {source_id}")
        else:
            # 字符串URL情况
            source_id = "string_url_source"
            current_url = source
            print(f"开始采集数据源 (URL): {current_url}")

        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 初始化变量
        all_content = []
        current_page = 1
        max_pages = 3  # 限制最大页数，避免无限循环

        while current_page <= max_pages:
            print(f"正在采集第 {current_page} 页: {current_url}")
            html_content = ""

            try:
                # 发送请求
                response = requests.get(
                    current_url, headers=headers, timeout=15)
                response.raise_for_status()

                # 处理编码
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding

                html_content = response.text

                # 使用简单的正则表达式提取标题和链接
                print("正在提取页面中的链接和标题...")
                title_link_pairs = extract_titles_and_links_simple(
                    html_content, current_url)
                print(f"成功提取到 {len(title_link_pairs)} 个标题链接对")

                if not title_link_pairs:
                    print(f"第 {current_page} 页未找到有效链接，尝试其他方式...")

                    # 直接从当前页面提取文本内容作为后备
                    clean_text = re.sub(r'<[^>]+>', '', html_content)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if len(clean_text) > 500:
                        all_content.append(
                            f"页面内容: {current_url}\n{clean_text[:2000]}...")

                    # 查找下一页
                    next_url = find_next_page_link(html_content, current_url)
                    if next_url:
                        current_url = next_url
                        current_page += 1
                        time.sleep(2)
                        continue
                    else:
                        break

                # 跟进链接获取文章内容
                articles_content = []
                article_limit = min(5, len(title_link_pairs))  # 减少获取文章数量
                print(f"将获取前 {article_limit} 篇文章的详细内容")

                for i, (title, link) in enumerate(title_link_pairs[:article_limit]):
                    try:
                        print(f"[{i+1}/{article_limit}] 正在获取文章: {title}")
                        # 获取文章内容
                        article_content = fetch_article_content_simple(
                            link, headers)

                        if article_content and len(article_content) > 200:
                            # 创建文章信息字典
                            article_info = {
                                "title": title,
                                "url": link,
                                "content": article_content,
                                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            articles_content.append(article_info)
                            print(f"[{i+1}/{article_limit}] 成功处理文章: {title}")
                        else:
                            print(
                                f"[{i+1}/{article_limit}] 文章内容过短或为空，跳过: {title}")

                        # 随机延时
                        delay = random.uniform(1.0, 2.0)  # 减少延时时间
                        print(f"等待 {delay:.2f} 秒再获取下一篇文章...")
                        time.sleep(delay)
                    except Exception as e:
                        print(f"[{i+1}/{article_limit}] 获取文章 {title} 时出错: {e}")
                        time.sleep(1)

                # 添加到总内容
                if articles_content:
                    all_content.extend(articles_content)
                    print(
                        f"第 {current_page} 页成功获取 {len(articles_content)} 篇文章内容")

            except Exception as page_error:
                print(f"处理第 {current_page} 页时出错: {page_error}")

            # 查找下一页链接
            next_url = find_next_page_link(html_content, current_url)

            # 继续翻页
            if next_url:
                current_url = next_url
                current_page += 1
                print(f"准备采集下一页: {current_url}")
                time.sleep(2)  # 减少延时
            else:
                print("未找到下一页链接或已达到最大页数，结束翻页")
                break

        # 处理采集结果
        if all_content:
            print(f"总共成功获取 {len(all_content)} 条内容")
            return all_content
        else:
            print("未获取到任何有效文章内容")
            return []

    except Exception as e:
        print(f"采集数据主流程出错: {e}")
        import traceback
        traceback.print_exc()
        return []


def extract_titles_and_links_simple(html_content, base_url):
    """
    从HTML中提取标题和链接
    :param html_content: HTML内容
    :param base_url: 基础URL
    :return: 标题和链接的列表
    """
    title_link_pairs = []

    # 定义多种链接提取模式，增加匹配成功率
    patterns = [
        # 东方财富网热点文章链接
        r'<a[^>]*href=["\'](https?://finance\.eastmoney\.com/a/[^"\']*?)["\'][^>]*>(.*?)</a>',
        r'<a[^>]*href=["\'](/a/[^"\']*?)["\'][^>]*>(.*?)</a>',
        # 新浪财经文章链接
        r'<a[^>]*href=["\'](https?://finance\.sina\.com\.cn/[^"\']*?)["\'][^>]*>(.*?)</a>',
        r'<a[^>]*href=["\'](https?://[^\.]+\.sina\.com\.cn/[^"\']*?)["\'][^>]*>(.*?)</a>',
        # 凤凰财经文章链接
        r'<a[^>]*href=["\'](https?://finance\.ifeng\.com/c/[^"\']*?)["\'][^>]*>(.*?)</a>',
        r'<a[^>]*href=["\'](https?://[^\.]+\.ifeng\.com/[^"\']*?)["\'][^>]*>(.*?)</a>',
        # 和讯网文章链接
        r'<a[^>]*href=["\'](https?://www\.hexun\.com/[^"\']*?)["\'][^>]*>(.*?)</a>',
        # 通用新闻链接模式
        r'<a[^>]*class=["\'][^"\']*(?:news|article|title)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\'][^>]*>([^<]{5,}?)</a>',
        r'<a[^>]*href=["\']([^"\']*?news[^"\']*?)["\'][^>]*>([^<]{5,}?)</a>',
        r'<a[^>]*href=["\']([^"\']*?article[^"\']*?)["\'][^>]*>([^<]{5,}?)</a>',
        r'<a[^>]*href=["\']([^"\']*?story[^"\']*?)["\'][^>]*>([^<]{5,}?)</a>',
        # 通用链接模式
        r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>([^<]{8,}?)</a>'
    ]

    # 尝试每种模式提取链接和标题
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)

        for href, title in matches:
            # 清理标题，移除HTML标签
            clean_title = re.sub(r'<[^>]+>', '', title).strip()
            clean_title = re.sub(r'\s+', ' ', clean_title)

            # 过滤有效的标题和链接
            if clean_title and len(clean_title) > 5 and href:
                # 排除一些不需要的链接类型
                if href.startswith('#') or 'javascript:' in href.lower() or 'mailto:' in href.lower():
                    continue

                # 处理相对链接，确保是完整URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = urljoin(base_url, href)
                elif not href.startswith('http'):
                    href = urljoin(base_url, href)

                # 避免重复添加相同标题的链接
                if not any(pair[0] == clean_title for pair in title_link_pairs):
                    title_link_pairs.append((clean_title, href))

        # 如果已经找到足够多的链接，可以提前结束
        if len(title_link_pairs) >= 15:
            break

    # 去重，保留第一个出现的链接
    unique_pairs = []
    seen_titles = set()
    seen_links = set()
    for title, link in title_link_pairs:
        if title not in seen_titles and link not in seen_links and len(unique_pairs) < 25:  # 限制最大数量
            seen_titles.add(title)
            seen_links.add(link)
            unique_pairs.append((title, link))

    return unique_pairs


def fetch_article_content_simple(url, headers=None):
    """
    从网页URL获取文章内容（简单版）
    :param url: 文章URL
    :param headers: 请求头
    :return: 文章内容
    """
    try:
        if not headers:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': 'https://www.google.com/'
            }

        # 检查URL是否有效
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            print(f"无效URL: {url}")
            return ""

        # 发送请求，设置超时
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()  # 检查HTTP错误

        # 自动检测和设置编码
        if response.encoding == 'ISO-8859-1':
            response.encoding = response.apparent_encoding

        html_content = response.text

        # 提取标题
        title_match = re.search(
            r'<title[^>]*>(.*?)</title>', html_content, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else '未命名文章'

        # 提取文章内容 - 使用全面的内容容器匹配模式
        content_patterns = [
            # 东方财富网特定内容容器
            r'<div[^>]*class=["\'](?:artibody|article-body|articleContent|content-main)["\'](?:\s[^>]*>|>)(.*?)</div>',
            r'<div[^>]*id=["\']artibody["\'](?:\s[^>]*>|>)(.*?)</div>',
            # 新浪财经特定内容容器
            r'<div[^>]*class=["\'](?:article|artContent|article-body|main-content)["\'](?:\s[^>]*>|>)(.*?)</div>',
            r'<div[^>]*id=["\']artibody["\'](?:\s[^>]*>|>)(.*?)</div>',
            # 凤凰财经特定内容容器
            r'<div[^>]*class=["\'](?:text-3wQ7Q|content|article-body|article-main)["\'](?:\s[^>]*>|>)(.*?)</div>',
            r'<div[^>]*id=["\']main_content["\'](?:\s[^>]*>|>)(.*?)</div>',
            # 和讯网特定内容容器
            r'<div[^>]*class=["\'](?:art_content|article-content|content-main|articleBody)["\'](?:\s[^>]*>|>)(.*?)</div>',
            # 常见文章内容容器类名
            r'<div[^>]*class=["\'](?:article-content|articleBody|content|newsContent|article|main-content|article-detail)["\'](?:\s[^>]*>|>)(.*?)</div>',
            # ID属性匹配
            r'<div[^>]*id=["\'](?:content|article|news|articleContent|main)["\'](?:\s[^>]*>|>)(.*?)</div>',
            # 语义化标签
            r'<article[^>]*>(.*?)</article>',
            r'<section[^>]*class=["\'](?:content|article)["\'](?:\s[^>]*>|>)(.*?)</section>',
            # 段落内容 - 备选方案
            r'<div[^>]*>(?:<p>.*?</p>\s*)+</div>'  # 包含多个段落的div
        ]

        content = ""
        # 尝试每种内容提取模式
        for pattern in content_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1)
                # 如果提取到的内容超过100个字符，认为有效
                if len(re.sub(r'<[^>]+>', '', content).strip()) > 150:
                    break

        # 如果没找到特定容器，尝试获取所有段落内容
        if not content or len(re.sub(r'<[^>]+>', '', content).strip()) <= 150:
            print(f"未找到标准内容容器，尝试提取段落内容: {url}")
            # 提取所有段落文本
            paragraphs = re.findall(
                r'<p[^>]*>(.*?)</p>', html_content, re.IGNORECASE | re.DOTALL)
            if paragraphs:
                # 连接所有段落，过滤掉过短的段落
                content = ' '.join([p for p in paragraphs if len(
                    re.sub(r'<[^>]+>', '', p).strip()) > 20])
            
            # 如果段落内容也不足，尝试提取所有文本内容
            if not content or len(content) < 200:
                print(f"段落内容不足，尝试提取所有文本: {url}")
                # 移除脚本和样式
                text_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
                text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL | re.IGNORECASE)
                # 移除所有HTML标签
                text_content = re.sub(r'<[^>]+>', '', text_content)
                # 清理文本
                text_content = re.sub(r'\s+', ' ', text_content)
                text_content = text_content.strip()
                if len(text_content) > 300:
                    content = text_content[:3000]  # 限制长度

        # 清理HTML标签和多余空格
        if content:
            # 移除脚本和样式
            clean_content = re.sub(
                r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            clean_content = re.sub(
                r'<style[^>]*>.*?</style>', '', clean_content, flags=re.DOTALL | re.IGNORECASE)
            # 移除HTML注释
            clean_content = re.sub(
                r'<!--.*?-->', '', clean_content, flags=re.DOTALL)
            # 移除所有HTML标签
            clean_content = re.sub(r'<[^>]+>', '', clean_content)
            # 替换多个空格为单个空格
            clean_content = re.sub(r'\s+', ' ', clean_content)
            # 清理首尾空格
            clean_content = clean_content.strip()

            # 进一步清理特殊字符
            clean_content = re.sub(r'&nbsp;', ' ', clean_content)
            clean_content = re.sub(r'&amp;', '&', clean_content)
            clean_content = re.sub(r'&lt;', '<', clean_content)
            clean_content = re.sub(r'&gt;', '>', clean_content)
            clean_content = re.sub(r'&quot;', '"', clean_content)
            clean_content = re.sub(r'&#39;', "'", clean_content)

            # 如果内容太短，尝试其他方式
            if len(clean_content) < 200:
                print(f"提取的内容过短 ({len(clean_content)} 字符)，尝试其他方式: {url}")
                # 尝试使用更宽松的正则表达式
                loose_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
                if loose_match:
                    body_content = loose_match.group(1)
                    body_text = re.sub(r'<[^>]+>', '', body_content)
                    body_text = re.sub(r'\s+', ' ', body_text).strip()
                    if len(body_text) > 500:
                        clean_content = body_text[:2000]  # 取前2000字符

            print(f"成功获取文章内容，长度: {len(clean_content)} 字符")
            # 返回完整文章内容
            return clean_content
        else:
            print(f"未能提取到有效内容: {url}")

        return ""
    except requests.exceptions.RequestException as e:
        print(f"请求文章失败 {url}: {e}")
        return ""
    except Exception as e:
        print(f"获取文章内容时发生错误 {url}: {e}")
        import traceback
        traceback.print_exc()
        return ""


def find_next_page_link(html_content, current_url):
    """
    查找下一页链接 - 增强版
    :param html_content: 当前页面HTML内容
    :param current_url: 当前页面URL
    :return: 下一页URL
    """
    try:
        print("正在查找下一页链接...")

        # 扩充的下一页链接模式，覆盖更多网站的分页格式
        next_patterns = [
            # 中文下一页文本匹配 - 更通用的模式
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*下一页\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*下页\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*下\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*&gt;&gt;\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*&gt;\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*>>\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*>\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*下一页\s*</a>',
            # 英文下一页文本匹配
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*Next\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*next page\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*older posts\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>\s*more\s*</a>',
            # 基于class属性的匹配 - 更通用的模式
            r'<a[^>]*class=["\'](?:[^"\']*\s|)next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'](?:[^"\']*\s|)pager-next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'](?:[^"\']*\s|)pagination-next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'](?:[^"\']*\s|)page-next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'](?:[^"\']*\s|)next-page(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'](?:[^"\']*\s|)pages-next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于id属性的匹配
            r'<a[^>]*id=["\'](?:[^"\']*\s|)next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*id=["\'](?:[^"\']*\s|)page-next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于title属性的匹配
            r'<a[^>]*title=["\'](?:[^"\']*\s|)next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*title=["\'](?:[^"\']*\s|)下一页(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于rel属性的匹配（规范的分页实现）
            r'<a[^>]*rel=["\'](?:[^"\']*\s|)next(?:\s[^"\']*|)["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于页码参数的匹配
            r'<a[^>]*href=["\']([^"\']*?page=)(\d+)([^"\']*?)["\'][^>]*>\s*\2\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?p=)(\d+)([^"\']*?)["\'][^>]*>\s*\2\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?page/)(\d+)([^"\']*?)["\'][^>]*>\s*\2\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?/page/)(\d+)([^"\']*?)["\'][^>]*>\s*\2\s*</a>',
            # 东方财富网特定模式
            r'<a[^>]*href=["\'](/.*?page_\d+\.html)["\'][^>]*>\s*下一页\s*</a>',
            r'<a[^>]*href=["\'](https?://finance\.eastmoney\.com/.*?page_\d+\.html)["\'][^>]*>',
            r'<a[^>]*href=["\'](/.*?index_\d+\.html)["\'][^>]*>\s*下一页\s*</a>',
            # 新浪财经特定模式
            r'<a[^>]*href=["\'](https?://finance\.sina\.com\.cn/.*?page=\d+)["\'][^>]*>',
            r'<a[^>]*href=["\'](https?://[^\.]+\.sina\.com\.cn/.*?page=\d+)["\'][^>]*>',
            # 凤凰财经特定模式
            r'<a[^>]*href=["\'](https?://finance\.ifeng\.com/.*?/page/\d+)["\'][^>]*>',
            # 和讯网特定模式
            r'<a[^>]*href=["\'](https?://www\.hexun\.com/.*?page=\d+)["\'][^>]*>',
            # 其他通用模式
            r'<a[^>]*href=["\']([^"\']*?)/page/\d+["\'][^>]*>\s*下一页\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)\?page=\d+["\'][^>]*>\s*下一页\s*</a>',
            r'<a[^>]*href=["\']([^"\']*?)&page=\d+["\'][^>]*>\s*下一页\s*</a>'
        ]

        # 尝试提取当前页码，用于页码匹配
        current_page_num = None
        try:
            # 从URL中提取页码 - 尝试多种格式
            page_patterns = [
                r'page=(\d+)',
                r'p=(\d+)',
                r'/page/(\d+)',
                r'index_(\d+)\.html',
                r'page_(\d+)\.html'
            ]
            
            for page_pattern in page_patterns:
                page_match = re.search(page_pattern, current_url)
                if page_match:
                    current_page_num = int(page_match.group(1))
                    print(f"从URL识别当前页码: {current_page_num}")
                    break
        except Exception as e:
            print(f"提取当前页码时出错: {e}")
            pass

        # 尝试每种模式查找下一页链接
        for pattern in next_patterns:
            match = re.search(pattern, html_content, re.IGNORECASE)
            if match:
                # 特殊处理页码匹配模式
                if len(match.groups()) == 3 and current_page_num is not None:
                    base_url = match.group(1)
                    page_num = int(match.group(2))
                    suffix = match.group(3)
                    # 检查是否为下一页
                    if page_num > current_page_num:
                        next_url = f"{base_url}{page_num}{suffix}"
                        print(f"通过页码模式找到下一页链接: {next_url}")
                    else:
                        continue
                else:
                    next_url = match.group(1)

                # 处理相对链接
                if next_url.startswith('//'):
                    next_url = 'https:' + next_url
                elif next_url.startswith('/'):
                    next_url = urljoin(current_url, next_url)
                elif not next_url.startswith('http'):
                    next_url = urljoin(current_url, next_url)

                # 确保不是当前页的锚点链接
                if '#' in next_url and next_url.split('#')[0] == current_url.split('#')[0]:
                    continue

                # 确保不是JavaScript链接
                if next_url.startswith('javascript:'):
                    continue

                print(f"找到下一页链接: {next_url}")
                return next_url

        # 如果没有找到标准的下一页链接，尝试手动构造下一页URL
        try:
            # 尝试基于当前URL构造下一页URL
            if current_page_num is not None:
                next_page_num = current_page_num + 1
                # 尝试替换URL中的页码
                next_url = re.sub(r'page=(\d+)', f'page={next_page_num}', current_url)
                if next_url != current_url:
                    print(f"手动构造下一页链接: {next_url}")
                    return next_url
                    
                next_url = re.sub(r'p=(\d+)', f'p={next_page_num}', current_url)
                if next_url != current_url:
                    print(f"手动构造下一页链接: {next_url}")
                    return next_url
                    
                next_url = re.sub(r'/page/(\d+)', f'/page/{next_page_num}', current_url)
                if next_url != current_url:
                    print(f"手动构造下一页链接: {next_url}")
                    return next_url
                    
                next_url = re.sub(r'index_(\d+)\.html', f'index_{next_page_num}\.html', current_url)
                if next_url != current_url:
                    print(f"手动构造下一页链接: {next_url}")
                    return next_url
                    
                next_url = re.sub(r'page_(\d+)\.html', f'page_{next_page_num}\.html', current_url)
                if next_url != current_url:
                    print(f"手动构造下一页链接: {next_url}")
                    return next_url
        except Exception as e:
            print(f"手动构造下一页链接时出错: {e}")

        print("未找到符合模式的下一页链接")
        return None
    except Exception as e:
        print(f"查找下一页链接时出错: {e}")
        import traceback
        traceback.print_exc()
        return None

# 热点新闻采集


def fetch_newsWeb_data(source: Source) -> List[str]:
    """
    采集热点新闻数据
    :param source: 数据源对象
    :return: 文本列表
    """
    try:
        print(f"开始采集热点新闻数据源: {source.url}")

        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 初始化变量
        all_content = []
        current_page = 1
        max_pages = 3  # 限制最大页数

        while current_page <= max_pages:
            print(f"正在采集第 {current_page} 页: {current_url}")
            html_content = ""

            try:
                # 发送请求
                response = requests.get(
                    current_url, headers=headers, timeout=15)
                response.raise_for_status()

                # 处理编码
                if response.encoding == 'ISO-8859-1':
                    response.encoding = response.apparent_encoding

                html_content = response.text

                # 提取标题和链接
                print("正在提取页面中的链接和标题...")
                title_link_pairs = extract_titles_and_links_simple(
                    html_content, current_url)
                print(f"成功提取到 {len(title_link_pairs)} 个标题链接对")

                # 跟进链接获取文章内容
                articles_content = []
                article_limit = min(8, len(title_link_pairs))  # 每页获取的文章数量
                print(f"将获取前 {article_limit} 篇文章的详细内容")

                for i, (title, link) in enumerate(title_link_pairs[:article_limit]):
                    try:
                        print(f"[{i+1}/{article_limit}] 正在获取文章: {title}")
                        # 获取文章内容
                        article_content = fetch_article_content_simple(
                            link, headers)

                        if article_content and len(article_content) > 200:
                            article_info = {
                                "title": title,
                                "url": link,
                                "content": article_content,
                                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            articles_content.append(article_info)
                            print(f"[{i+1}/{article_limit}] 成功处理文章: {title}")
                        else:
                            print(
                                f"[{i+1}/{article_limit}] 文章内容过短或为空，跳过: {title}")

                        # 随机延时
                        delay = random.uniform(0.5, 1.5)
                        time.sleep(delay)
                    except Exception as e:
                        print(f"[{i+1}/{article_limit}] 获取文章 {title} 时出错: {e}")
                        time.sleep(1)

                # 添加到总内容
                if articles_content:
                    all_content.extend(articles_content)
                    print(
                        f"第 {current_page} 页成功获取 {len(articles_content)} 篇文章内容")

            except Exception as page_error:
                print(f"处理第 {current_page} 页时出错: {page_error}")

            # 查找下一页链接
            next_url = find_next_page_link(html_content, current_url)

            # 继续翻页
            if next_url:
                current_url = next_url
                current_page += 1
                print(f"准备采集下一页: {current_url}")
                time.sleep(2)
            else:
                print("未找到下一页链接或已达到最大页数，结束翻页")
                break

        # 处理采集结果
        if all_content:
            print(f"总共成功获取 {len(all_content)} 条内容")
            return all_content
        else:
            print("未获取到任何有效文章内容")
            return []

    except Exception as e:
        print(f"采集热点新闻数据时出错: {e}")
        return []