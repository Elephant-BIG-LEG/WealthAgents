from langchain_openai import ChatOpenAI
from app.parse.parsing import parse_data
import requests
import re
from html.parser import HTMLParser
from typing import List
from app.config.config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL
from app.ingest.source import Source
from langchain_core.prompts import ChatPromptTemplate
import time
import random
from urllib.parse import urlparse, urljoin

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
def Collection_action_llm(source: Source) -> List[str]:
    """
    根据数据源执行采集动作
    :param source: 数据源对象
    :return: 采集到的数据列表
    """
    if source.type == "web":
        return fetch_financeWeb_data(source)
    elif source.type == "news":
        return fetch_newsWeb_data(source)
    return []


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


def fetch_financeWeb_data(source: Source) -> List[str]:
    """
    采集财经网站数据（增强版 - 支持自动翻页和文章内容获取）
    :param source: 数据源对象
    :return: 采集到的数据列表
    """
    try:
        print(f"开始采集数据源: {source.source_id}")

        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        # 初始化变量
        all_content = []
        # 优先使用source.url，如果为空则使用source.source_id (兼容旧代码逻辑)
        current_url = source.url if source.url else source.source_id
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
                            article_info = f"标题: {title}\n链接: {link}\n内容: {article_content}"
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
        # 模式1: 新闻文章链接特征 - 东方财富网等
        r'<a[^>]*href=["\']([^"\']*?/a/[^"\']*?)["\'][^>]*>(.*?)</a>',
        # 模式2: 通用链接模式，包含新闻、文章关键词
        r'<a[^>]*href=["\']([^"\']*?)(?:news|article|story)[^"\']*?["\'][^>]*>(.*?)</a>',
        # 模式3: 通用标题链接模式，捕获任何可能的链接和标题
        r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>([^<]{5,}?)</a>',
        # 模式4: 带有class属性的链接（常见于新闻列表）
        r'<a[^>]*class=["\'][^"\']*(?:title|news|article)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\'][^>]*>(.*?)</a>',
        # 模式5: 带有id属性的链接
        r'<a[^>]*id=["\'][^"\']*(?:title|news|article)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\'][^>]*>(.*?)</a>'
    ]

    # 尝试每种模式提取链接和标题
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)

        for href, title in matches:
            # 清理标题，移除HTML标签
            clean_title = re.sub(r'<[^>]+>', '', title).strip()

            # 过滤有效的标题和链接
            if clean_title and len(clean_title) > 5 and href:
                # 排除一些不需要的链接类型
                if href.startswith('#') or 'javascript:' in href.lower():
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
        if len(title_link_pairs) >= 10:
            break

    # 去重，保留第一个出现的链接
    unique_pairs = []
    seen_titles = set()
    for title, link in title_link_pairs:
        if title not in seen_titles and len(unique_pairs) < 20:  # 限制最大数量
            seen_titles.add(title)
            unique_pairs.append((title, link))

    return unique_pairs


def fetch_article_content_simple(url, headers=None):
    """
    简单获取文章内容
    :param url: 文章URL
    :param headers: 请求头（可选）
    :return: 文章内容
    """
    try:
        print(f"正在获取文章URL: {url}")

        # 设置默认请求头
        if headers is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

        # 检查URL是否有效
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            print(f"无效URL: {url}")
            return ""

        # 发送请求，设置超时
        response = requests.get(url, headers=headers, timeout=15)
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
            # 常见文章内容容器类名
            r'<div[^>]*class="[^"]*article-content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*articleBody[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*newsContent[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*main-content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*class="[^"]*article-detail[^"]*"[^>]*>(.*?)</div>',
            # ID属性匹配
            r'<div[^>]*id="[^"]*content[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*article[^"]*"[^>]*>(.*?)</div>',
            r'<div[^>]*id="[^"]*news[^"]*"[^>]*>(.*?)</div>',
            # 语义化标签
            r'<article[^>]*>(.*?)</article>',
            r'<section[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</section>',
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
                if len(re.sub(r'<[^>]+>', '', content).strip()) > 100:
                    break

        # 如果没找到特定容器，尝试获取所有段落内容
        if not content or len(re.sub(r'<[^>]+>', '', content).strip()) <= 100:
            print(f"未找到标准内容容器，尝试提取段落内容: {url}")
            # 提取所有段落文本
            paragraphs = re.findall(
                r'<p[^>]*>(.*?)</p>', html_content, re.IGNORECASE | re.DOTALL)
            if paragraphs:
                # 连接所有段落，过滤掉过短的段落
                content = ' '.join([p for p in paragraphs if len(
                    re.sub(r'<[^>]+>', '', p).strip()) > 10])

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
            # 中文下一页文本匹配
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>下一页</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>下一页</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>下页</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>&gt;&gt;</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>&gt;</a>',
            # 英文下一页文本匹配
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>Next</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>next page</a>',
            r'<a[^>]*href=["\']([^"\']*?)["\'][^>]*>older posts</a>',
            # 基于class属性的匹配
            r'<a[^>]*class=["\'][^"\']*(?:next|pager-next|pagination-next)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\']',
            r'<a[^>]*class=["\'][^"\']*page[^"\']*["\'][^>]*href=["\']([^"\']*?)["\'][^>]*>\s*\d+\s*</a>',
            # 基于id属性的匹配
            r'<a[^>]*id=["\'][^"\']*(?:next|page-next)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于title属性的匹配
            r'<a[^>]*title=["\'][^"\']*(?:next|下一页)[^"\']*["\'][^>]*href=["\']([^"\']*?)["\']',
            # 基于rel属性的匹配（规范的分页实现）
            r'<a[^>]*rel=["\']next["\'][^>]*href=["\']([^"\']*?)["\']',
            # 页码匹配 - 查找大于当前页码的链接
            r'<a[^>]*href=["\']([^"\']*?page=)(\d+)([^"\']*?)["\'][^>]*>\s*\2\s*</a>'
        ]

        # 尝试提取当前页码，用于页码匹配
        current_page_num = None
        try:
            # 从URL中提取页码
            page_match = re.search(r'page=(\d+)', current_url)
            if page_match:
                current_page_num = int(page_match.group(1))
                print(f"从URL识别当前页码: {current_page_num}")
        except Exception:
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

                print(f"找到下一页链接: {next_url}")
                return next_url

        print("未找到符合模式的下一页链接")
        return None
    except Exception as e:
        print(f"查找下一页链接时出错: {e}")
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
        current_url = source.url
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
                            article_info = f"标题: {title}\n链接: {link}\n内容: {article_content}"
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
