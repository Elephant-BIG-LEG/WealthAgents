"""
财富Agent - 智能投研分析平台
UI模块 - Web应用主入口
集成Plan → Act → Reflect决策闭环的私人Agent
"""

from app.config.config import DB_CONFIG
from app.ingest.source import Source
from app.ingest.web_fetcher import Collection_action_llm
from app.agentWorker.data_summarizer import LangChainHelperWithSummary
from app.agentWorker.data_parse_and_process import LangChainHelperWithIntegration
from app.agent.private_agent import PrivateAgent  # 导入新的Agent框架
import json
import logging
import os
import sys
import traceback
import datetime

from flask import Flask, request, jsonify, render_template
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

# 导入数据处理和总结的工具类

# 创建Flask应用，明确指定模板目录
# 获取当前文件的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 模板目录是当前目录下的templates文件夹
template_dir = os.path.join(current_dir, 'templates')
print(f"Template directory: {template_dir}")  # 调试信息

app = Flask(__name__, template_folder=template_dir)

# 创建全局Agent实例
agent = PrivateAgent()

# 数据库连接信息（从配置文件读取）
DB_CONFIG = DB_CONFIG

# 数据库连接函数


def get_db_connection():
    try:
        # 使用pymysql直接连接
        import pymysql
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        logging.error(f"数据库连接失败: {str(e)}")
        return None


# 处理跨域预检请求


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers',
                         'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods',
                         'GET,PUT,POST,DELETE,OPTIONS')
    return response


# 处理OPTIONS预检请求


@app.route('/collect', methods=['OPTIONS'])
def collect_options():
    from werkzeug.wrappers import Response
    response = Response()
    response.status_code = 200
    return response


# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量存储采集的数据
collected_data = []

# 初始化数据处理和总结助手
parser_helper = LangChainHelperWithIntegration()
summarizer_helper = LangChainHelperWithSummary()

# 主页路由 - 仪表盘


@app.route('/')
def index():
    return render_template('dashboard.html')


# 数据采集页面


@app.route('/data-collection')
def data_collection():
    return render_template('data_collection.html')


# 近期热点页面


@app.route('/recent-hotspots')
def recent_hotspots():
    return render_template('recent_hotspots.html')


# 股票分析页面


@app.route('/stock-analysis')
def stock_analysis():
    return render_template('stock_analysis.html')


# 财务分析页面


@app.route('/financial-analysis')
def financial_analysis():
    return render_template('financial_analysis.html')


# 私人Agent页面


@app.route('/private-agent')
def private_agent():
    return render_template('private_agent.html')


# 往期数据页面


@app.route('/historical-data')
def historical_data():
    return render_template('historical_data.html')


# 设置页面


@app.route('/settings')
def settings():
    return render_template('settings.html')


# 新增：私人Agent API端点 - 处理与Agent的交互
@app.route('/api/agent/chat', methods=['POST'])
def agent_chat():
    """
    与私人Agent的聊天API端点
    接收用户消息并返回Agent的响应
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        session_id = data.get('session_id')  # 可选的会话ID

        if not user_message:
            return jsonify({
                'success': False,
                'message': '消息内容不能为空'
            })

        # 调用Agent进行处理
        # TODO
        response = agent.chat(user_message, session_id)

        if response['status'] == 'success':
            return jsonify({
                'success': True,
                'response': response['response'],
                'session_id': response['session_id'],
                'detailed_result': response.get('detailed_result', {})
            })
        else:
            return jsonify({
                'success': False,
                'message': response.get('error_message', '处理请求时发生错误')
            })

    except Exception as e:
        logger.error(f"处理Agent聊天请求时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}'
        })


# API路由 - 仪表盘统计数据


@app.route('/api/dashboard/stats')
def dashboard_stats():
    try:
        # 获取数据库连接
        conn = get_db_connection()
        stats = {
            'total_data': 0,
            'hot_topics': 0,
            'stock_analysis': 0,
            'agent_tasks': 0
        }

        if conn:
            cursor = conn.cursor()
            try:
                # 获取总数据量
                cursor.execute("SELECT COUNT(*) as count FROM recenthottopics")
                result = cursor.fetchone()
                stats['total_data'] = result['count'] if result else 0

                # 获取热点话题数量
                cursor.execute(
                    "SELECT COUNT(DISTINCT topic) as count FROM recenthottopics")
                result = cursor.fetchone()
                stats['hot_topics'] = result['count'] if result else 0

                # 获取最近30天的数据量作为股票分析数量
                cursor.execute("""
                    SELECT COUNT(*) as count FROM recenthottopics 
                    WHERE created_ts >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                """)
                result = cursor.fetchone()
                stats['stock_analysis'] = result['count'] if result else 0

                # Agent任务数量（这里简化处理）
                stats['agent_tasks'] = stats['total_data']

            except Exception as e:
                logger.error(f"查询统计数据失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()

        # 获取最近热点数据
        recent_hotspots = []
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT id, topic, market_summary as summary, source, created_ts as timestamp 
                    FROM recenthottopics 
                    ORDER BY created_ts DESC 
                    LIMIT 5
                """)
                recent_hotspots = cursor.fetchall()
            except Exception as e:
                logger.error(f"查询热点数据失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()

        # Agent结论（模拟数据）
        agent_conclusions = [
            {
                'title': '市场趋势判断',
                'conclusion': '当前市场处于震荡整理阶段，建议关注政策面变化',
                'timestamp': '2023-12-15 09:30'
            },
            {
                'title': '行业配置建议',
                'conclusion': '建议超配科技和消费板块，低配金融地产',
                'timestamp': '2023-12-14 16:00'
            }
        ]

        # 采集状态（模拟数据）
        collection_status = [
            {
                'source': '东方财富网',
                'status': 'completed',
                'timestamp': '2023-12-15 09:15'
            },
            {
                'source': '新浪财经',
                'status': 'failed',
                'timestamp': '2023-12-15 08:45'
            }
        ]

        return jsonify({
            'success': True,
            'stats': stats,
            'recent_hotspots': recent_hotspots,
            'agent_conclusions': agent_conclusions,
            'collection_status': collection_status
        })
    except Exception as e:
        logger.error(f"获取仪表盘数据失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}'
        })


@app.route('/collect', methods=['POST'])
def collect_data():
    try:
        # 记录请求信息
        logger.info("收到采集数据请求")
        logger.info(f"请求方法: {request.method}")
        logger.info(f"Content-Type: {request.content_type}")

        # 解析请求参数 - 支持JSON和表单数据格式
        source_url = None
        source_name = None
        source_type = None
        raw_data = None

        if request.is_json:
            data = request.get_json()
            logger.info(
                f"JSON请求 - source_type: {data.get('source_type')}, source_url: {data.get('source_url')}, source_name: {data.get('source_name')}")
            source_url = data.get('source_url')
            source_name = data.get('source_name')
            source_type = data.get('source_type')
            raw_data = data.get('data')
        else:
            # 处理表单数据
            source_url = request.form.get('source_url')
            source_name = request.form.get('source_name')
            source_type = request.form.get('source_type', 'web')  # 默认为web类型
            logger.info(
                f"表单请求 - source_type: {source_type}, source_url: {source_url}, source_name: {source_name}")

        # 验证必要参数
        if not source_url or not source_name:
            return jsonify({
                'success': False,
                'message': '请填写完整的网址和数据源名称',
                'data': None
            })

        # 执行实际的数据采集流程
        logger.info(f"开始从{source_name}({source_url})采集数据")

        # Step 1: 采集数据 - 调用网络爬虫获取数据
        if raw_data is None:
            # 创建数据源对象
            source = Source(source_id=source_url,
                            source_name=source_name, type=source_type)
            # 调用采集器获取数据
            collected_items = Collection_action_llm(source)
        else:
            collected_items = raw_data

        # 检查采集结果
        if collected_items is None:
            collected_items = []

        logger.info(f"成功采集到 {len(collected_items)} 条数据")

        # 如果没有采集到数据，返回错误信息
        if len(collected_items) == 0:
            return jsonify({
                'success': False,
                'message': '未能从指定网址采集到有效数据',
                'data': None
            })

        # Step 2: 使用大模型清洗和解析数据
        logger.info("开始使用大模型清洗和解析数据...")
        try:
            parsed_data = parser_helper.get_response(collected_items)
            logger.info("数据解析成功")
        except Exception as e:
            logger.error(f"大模型解析失败: {str(e)}")
            # 如果大模型解析失败，使用原始数据
            parsed_data = collected_items

        # Step 3: 使用大模型总结数据
        logger.info("开始使用大模型总结数据...")
        try:
            # 准备要总结的内容
            if isinstance(parsed_data, list):
                summary_input = '\n\n'.join(
                    [f"标题: {item.get('title', '')}\n内容: {item.get('content', item.get('summary', ''))}" for item in parsed_data])
            else:
                summary_input = str(parsed_data)

            summarized_data = summarizer_helper.get_response(summary_input)
            logger.info("数据总结成功")
        except Exception as e:
            logger.error(f"大模型总结失败: {str(e)}")
            # 如果大模型总结失败，创建默认总结数据
            summarized_data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'topic': f'从{source_name}采集的市场分析',
                'market_trend': '市场趋势分析',
                'investment_advice': '投资建议',
                'hotspot_summary': '热点总结'
            }

        # Step 4: 构建完整的数据项
        new_data_item = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'topic': summarized_data.get('topic', f'从{source_name}采集的数据') if isinstance(summarized_data, dict) else f'从{source_name}采集的数据',
            'market_trend': summarized_data.get('market_trend', '') if isinstance(summarized_data, dict) else '',
            'investment_advice': summarized_data.get('investment_advice', '') if isinstance(summarized_data, dict) else '',
            'hotspot_summary': summarized_data.get('hotspot_summary', '') if isinstance(summarized_data, dict) else '',
            'source_url': source_url,
            'source': source_name,
            'collection_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'raw_data': collected_items,
            'parsed_data': parsed_data
        }

        # 添加到全局变量
        collected_data.append(new_data_item)

        # Step 5: 写入数据库
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                # 构建SQL插入语句
                sql = """INSERT INTO recenthottopics 
                        (topic, article_content, investment_advice, market_summary, source) 
                        VALUES (%s, %s, %s, %s, %s)"""

                # 准备插入数据
                topic = new_data_item['topic']
                article_content = json.dumps(new_data_item, ensure_ascii=False)
                investment_advice = new_data_item['investment_advice']
                market_summary = new_data_item['market_trend']
                source = source_name

                # 执行插入
                cursor.execute(sql, (topic, article_content,
                               investment_advice, market_summary, source))
                conn.commit()

                logger.info(f"数据已成功写入数据库，ID: {cursor.lastrowid}")

            except Exception as e:
                conn.rollback()
                logger.error(f"数据库写入失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()

        return jsonify({
            'success': True,
            'message': '数据采集、处理和保存成功',
            'data_count': len(collected_items),
            'data': new_data_item,
            'summary': {
                'topic': new_data_item['topic'],
                'market_trend': new_data_item['market_trend'],
                'investment_advice': new_data_item['investment_advice']
            }
        })

    except Exception as e:
        logger.error(f"数据采集过程中发生错误: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}',
            'data': None
        })


@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        # 获取数据库中的数据（实际项目中会从数据库读取）
        conn = get_db_connection()
        data_list = []

        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT topic, article_content, investment_advice, market_summary, source FROM recenthottopics ORDER BY id DESC LIMIT 50")
                results = cursor.fetchall()

                # 格式化数据
                for row in results:
                    try:
                        # 尝试解析JSON字段
                        article_content = json.loads(row['article_content'])
                        data_list.append({
                            'topic': row['topic'],
                            'market_summary': row['market_summary'],
                            'investment_advice': row['investment_advice'],
                            'source': row['source'],
                            'date': article_content.get('date', '')
                        })
                    except:
                        # 如果解析失败，直接使用原始数据
                        data_list.append({
                            'topic': row['topic'],
                            'market_summary': row['market_summary'],
                            'investment_advice': row['investment_advice'],
                            'source': row['source']
                        })
            except Exception as e:
                logger.error(f"数据库查询失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()

        # 如果数据库中没有数据，使用全局变量中的数据
        if not data_list and collected_data:
            data_list = [{
                'topic': item['topic'],
                'market_summary': item['market_trend'],
                'investment_advice': item['investment_advice'],
                'source': item['source'],
                'date': item['date']
            } for item in collected_data]

        return jsonify({
            'success': True,
            'message': '数据获取成功',
            'data': data_list,
            'data_count': len(data_list),
            'count': len(data_list)  # 为了向后兼容
        })
    except Exception as e:
        logger.error(f"获取数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}',
            'data': None
        })


@app.route('/clear_data', methods=['POST'])
def clear_data():
    try:
        # 清除全局变量中的数据
        collected_data.clear()

        # 清除数据库中的数据（可选）
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM recenthottopics")
                conn.commit()
                logger.info("数据库中的数据已清除")
            except Exception as e:
                conn.rollback()
                logger.error(f"清除数据库数据失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()

        return jsonify({
            'success': True,
            'message': '数据已成功清除',
            'data': None
        })
    except Exception as e:
        logger.error(f"清除数据时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'服务器内部错误: {str(e)}',
            'data': None
        })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
