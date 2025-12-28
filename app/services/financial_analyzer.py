import json
import re
from typing import Dict, List, Any, Optional
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

"""
财务分析接口模块
提供公司财务数据的分析功能
"""


class FinancialAnalyzer:
    """财务分析器类"""

    def __init__(self):
        """初始化财务分析器"""
        # 初始化常用的财务指标计算公式
        self.financial_metrics = {
            'profit_margin': self._calculate_profit_margin,
            'return_on_assets': self._calculate_roa,
            'debt_to_equity': self._calculate_debt_to_equity,
            'current_ratio': self._calculate_current_ratio,
            'revenue_growth': self._calculate_revenue_growth,
            'profit_growth': self._calculate_profit_growth,
        }

        # 财务关键词，用于从非结构化文本中提取财务数据
        self.financial_keywords = {
            'revenue': ['收入', '营收', '销售额', '营业额', 'revenue', 'sales'],
            'profit': ['利润', '净利润', '税后利润', 'net profit', 'earnings'],
            'assets': ['资产', '总资产', 'assets', 'total assets'],
            'liabilities': ['负债', '总负债', 'liabilities', 'total liabilities'],
            'equity': ['股东权益', '净资产', 'equity', 'net worth'],
            'debt': ['债务', '借款', 'debt', 'loans'],
            'current_assets': ['流动资产', 'current assets'],
            'current_liabilities': ['流动负债', 'current liabilities'],
        }

    def analyze_financial_data(self, company_name: str, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析公司财务数据

        参数：
        - company_name: 公司名称
        - financial_data: 财务数据字典，包含各种财务指标

        返回：
        - 分析结果字典
        """
        try:
            logger.info(f"开始分析公司 {company_name} 的财务数据")

            results = {
                'company_name': company_name,
                'analysis_date': datetime.now().isoformat(),
                'financial_metrics': {},
                'financial_health': {},
                'growth_trends': {},
                'analysis_summary': ''
            }

            # 计算各种财务指标
            for metric_name, calculator in self.financial_metrics.items():
                try:
                    results['financial_metrics'][metric_name] = calculator(
                        financial_data)
                except Exception as e:
                    logger.warning(f"计算指标 {metric_name} 时出错: {str(e)}")
                    results['financial_metrics'][metric_name] = None

            # 评估财务健康状况
            results['financial_health'] = self._evaluate_financial_health(
                results['financial_metrics'])

            # 分析增长趋势
            if 'historical_data' in financial_data:
                results['growth_trends'] = self._analyze_growth_trends(
                    financial_data['historical_data'])

            # 生成分析摘要
            results['analysis_summary'] = self._generate_analysis_summary(
                results)

            logger.info(f"公司 {company_name} 的财务数据分析完成")
            return results

        except Exception as e:
            logger.error(f"分析公司 {company_name} 的财务数据时出错: {str(e)}")
            return {
                'error': f'分析失败: {str(e)}',
                'status': 'error'
            }

    def extract_financial_data_from_text(self, text: str) -> Dict[str, Any]:
        """
        从非结构化文本中提取财务数据

        参数：
        - text: 包含财务信息的文本

        返回：
        - 提取的财务数据字典
        """
        extracted_data = {}

        # 尝试提取关键财务数据
        for key, keywords in self.financial_keywords.items():
            value = self._extract_value_by_keywords(text, keywords)
            if value:
                extracted_data[key] = value

        # 尝试提取年份和季度信息
        extracted_data['year'] = self._extract_year(text)
        extracted_data['quarter'] = self._extract_quarter(text)

        return extracted_data

    def analyze_company_from_knowledge_base(self, company_name: str, knowledge_base) -> Dict[str, Any]:
        """
        从公司知识库中分析公司财务状况

        参数：
        - company_name: 公司名称
        - knowledge_base: 公司知识库管理器实例

        返回：
        - 分析结果字典
        """
        try:
            logger.info(f"从知识库中分析公司 {company_name} 的财务状况")

            # 查询与财务相关的内容
            financial_queries = [
                "财务报表", "财务数据", "收入", "利润", "资产负债表", "现金流量",
                "财务指标", "业绩", "盈利", "增长"
            ]

            all_financial_content = []
            for query in financial_queries:
                results = knowledge_base.query_company_knowledge(
                    company_name, query, top_k=3)
                for result in results:
                    if result['similarity'] > 0.5:  # 只考虑相似度高的内容
                        all_financial_content.append(result['text'])

            # 合并所有相关内容
            combined_text = "\n".join(all_financial_content)

            # 从合并的文本中提取财务数据
            extracted_data = self.extract_financial_data_from_text(
                combined_text)

            # 使用提取的数据进行财务分析
            if extracted_data:
                analysis_results = self.analyze_financial_data(
                    company_name, extracted_data)
                return {
                    'status': 'success',
                    'extracted_data': extracted_data,
                    'analysis_results': analysis_results
                }
            else:
                logger.warning(f"无法从知识库中提取到公司 {company_name} 的有效财务数据")
                return {
                    'status': 'insufficient_data',
                    'message': '无法从知识库中提取到足够的财务数据进行分析'
                }

        except Exception as e:
            logger.error(f"从知识库分析公司 {company_name} 时出错: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    def generate_financial_report(self, company_name: str, analysis_results: Dict[str, Any]) -> str:
        """
        生成格式化的财务分析报告

        参数：
        - company_name: 公司名称
        - analysis_results: 分析结果字典

        返回：
        - 格式化的报告文本
        """
        try:
            report = f"# {company_name} 财务分析报告\n\n"
            report += f"**分析日期**: {analysis_results.get('analysis_date', datetime.now().isoformat())}\n\n"

            # 添加财务指标部分
            if analysis_results.get('financial_metrics'):
                report += "## 财务指标\n\n"
                for metric, value in analysis_results['financial_metrics'].items():
                    if value is not None:
                        report += f"- **{self._get_metric_display_name(metric)}**: {self._format_metric_value(metric, value)}\n"

            # 添加财务健康状况评估
            if analysis_results.get('financial_health'):
                report += "\n## 财务健康状况\n\n"
                for aspect, assessment in analysis_results['financial_health'].items():
                    report += f"- **{aspect}**: {assessment}\n"

            # 添加增长趋势分析
            if analysis_results.get('growth_trends'):
                report += "\n## 增长趋势\n\n"
                for trend, data in analysis_results['growth_trends'].items():
                    report += f"- **{trend}**: {data}\n"

            # 添加分析摘要
            if analysis_results.get('analysis_summary'):
                report += "\n## 分析摘要\n\n"
                report += f"{analysis_results['analysis_summary']}\n"

            return report

        except Exception as e:
            logger.error(f"生成财务报告时出错: {str(e)}")
            return f"生成财务分析报告失败: {str(e)}"

    # 各种财务指标计算方法
    def _calculate_profit_margin(self, data: Dict[str, Any]) -> float:
        """计算利润率 = 利润 / 收入"""
        if 'profit' in data and 'revenue' in data and data['revenue'] != 0:
            return data['profit'] / data['revenue']
        return None

    def _calculate_roa(self, data: Dict[str, Any]) -> float:
        """计算资产回报率 = 利润 / 总资产"""
        if 'profit' in data and 'assets' in data and data['assets'] != 0:
            return data['profit'] / data['assets']
        return None

    def _calculate_debt_to_equity(self, data: Dict[str, Any]) -> float:
        """计算债务权益比 = 总负债 / 股东权益"""
        if 'liabilities' in data and 'equity' in data and data['equity'] != 0:
            return data['liabilities'] / data['equity']
        # 如果没有直接的负债数据，尝试用债务代替
        elif 'debt' in data and 'equity' in data and data['equity'] != 0:
            return data['debt'] / data['equity']
        return None

    def _calculate_current_ratio(self, data: Dict[str, Any]) -> float:
        """计算流动比率 = 流动资产 / 流动负债"""
        if ('current_assets' in data and 'current_liabilities' in data and
                data['current_liabilities'] != 0):
            return data['current_assets'] / data['current_liabilities']
        return None

    def _calculate_revenue_growth(self, data: Dict[str, Any]) -> float:
        """计算收入增长率"""
        if ('historical_data' in data and isinstance(data['historical_data'], list) and
                len(data['historical_data']) > 1):
            # 假设历史数据按时间顺序排列，最近的数据在最后
            current_revenue = data['historical_data'][-1].get('revenue')
            previous_revenue = data['historical_data'][-2].get('revenue')
            if current_revenue and previous_revenue and previous_revenue != 0:
                return (current_revenue - previous_revenue) / previous_revenue
        return None

    def _calculate_profit_growth(self, data: Dict[str, Any]) -> float:
        """计算利润增长率"""
        if ('historical_data' in data and isinstance(data['historical_data'], list) and
                len(data['historical_data']) > 1):
            # 假设历史数据按时间顺序排列，最近的数据在最后
            current_profit = data['historical_data'][-1].get('profit')
            previous_profit = data['historical_data'][-2].get('profit')
            if current_profit and previous_profit and previous_profit != 0:
                return (current_profit - previous_profit) / previous_profit
        return None

    # 辅助方法
    def _evaluate_financial_health(self, metrics: Dict[str, Any]) -> Dict[str, str]:
        """评估公司财务健康状况"""
        health_assessment = {}

        # 评估盈利能力
        if 'profit_margin' in metrics and metrics['profit_margin'] is not None:
            if metrics['profit_margin'] > 0.2:
                health_assessment['盈利能力'] = '很强'
            elif metrics['profit_margin'] > 0.1:
                health_assessment['盈利能力'] = '良好'
            elif metrics['profit_margin'] > 0:
                health_assessment['盈利能力'] = '一般'
            else:
                health_assessment['盈利能力'] = '较弱'

        # 评估偿债能力
        if 'debt_to_equity' in metrics and metrics['debt_to_equity'] is not None:
            if metrics['debt_to_equity'] < 0.5:
                health_assessment['偿债能力'] = '很强'
            elif metrics['debt_to_equity'] < 1:
                health_assessment['偿债能力'] = '良好'
            elif metrics['debt_to_equity'] < 2:
                health_assessment['偿债能力'] = '一般'
            else:
                health_assessment['偿债能力'] = '较弱'

        # 评估短期流动性
        if 'current_ratio' in metrics and metrics['current_ratio'] is not None:
            if metrics['current_ratio'] > 2:
                health_assessment['短期流动性'] = '很强'
            elif metrics['current_ratio'] > 1.5:
                health_assessment['短期流动性'] = '良好'
            elif metrics['current_ratio'] > 1:
                health_assessment['短期流动性'] = '一般'
            else:
                health_assessment['短期流动性'] = '较弱'

        return health_assessment

    def _analyze_growth_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """分析增长趋势"""
        trends = {}

        # 分析收入趋势
        revenues = [d.get('revenue')
                    for d in historical_data if 'revenue' in d]
        if len(revenues) > 1:
            growth = (revenues[-1] - revenues[0]) / \
                revenues[0] if revenues[0] != 0 else 0
            if growth > 0.3:
                trends['收入趋势'] = '快速增长'
            elif growth > 0:
                trends['收入趋势'] = '稳定增长'
            else:
                trends['收入趋势'] = '下降'

        # 分析利润趋势
        profits = [d.get('profit') for d in historical_data if 'profit' in d]
        if len(profits) > 1:
            growth = (profits[-1] - profits[0]) / \
                profits[0] if profits[0] != 0 else 0
            if growth > 0.3:
                trends['利润趋势'] = '快速增长'
            elif growth > 0:
                trends['利润趋势'] = '稳定增长'
            else:
                trends['利润趋势'] = '下降'

        return trends

    def _generate_analysis_summary(self, results: Dict[str, Any]) -> str:
        """生成分析摘要"""
        summary = f"基于对{results['company_name']}财务数据的分析，"

        # 根据财务健康状况生成摘要
        health = results.get('financial_health', {})
        if health:
            aspects = list(health.keys())
            if len(aspects) > 0:
                summary += f"该公司的{', '.join(aspects[:-1])}和{aspects[-1]}分别为{', '.join(health.values())}。"

        # 根据增长趋势生成摘要
        trends = results.get('growth_trends', {})
        if trends:
            summary += f"在增长方面，"
            for trend, status in trends.items():
                summary += f"{trend}为{status}，"

        # 添加建议或结论
        if 'debt_to_equity' in results['financial_metrics'] and \
           results['financial_metrics']['debt_to_equity'] is not None and \
           results['financial_metrics']['debt_to_equity'] > 2:
            summary += "建议关注公司的负债水平，考虑优化资本结构。"
        elif 'current_ratio' in results['financial_metrics'] and \
             results['financial_metrics']['current_ratio'] is not None and \
             results['financial_metrics']['current_ratio'] < 1:
            summary += "公司短期偿债能力较弱，需关注现金流状况。"
        else:
            summary += "整体来看，公司财务状况基本稳健。"

        return summary

    def _extract_value_by_keywords(self, text: str, keywords: List[str]) -> Optional[float]:
        """根据关键词从文本中提取数值"""
        for keyword in keywords:
            # 查找包含关键词的句子
            sentences = re.split(r'[。.!?\n]', text)
            for sentence in sentences:
                if keyword in sentence:
                    # 尝试提取数字
                    numbers = re.findall(
                        r'\d+(?:\.\d+)?(?:[万亿万千百]?)', sentence)
                    if numbers:
                        # 处理中国数字单位（万亿、亿、万）
                        return self._parse_chinese_number(numbers[-1])
        return None

    def _parse_chinese_number(self, num_str: str) -> float:
        """解析包含中文单位的数字"""
        multipliers = {
            '万': 10000,
            '亿': 100000000,
            '万亿': 1000000000000,
        }

        # 提取数字部分和单位部分
        match = re.match(r'(\d+(?:\.\d+)?)\s*([万亿万千百]*)', num_str)
        if match:
            num_part, unit_part = match.groups()
            num = float(num_part)

            # 应用单位乘数
            for unit, multiplier in multipliers.items():
                if unit in unit_part:
                    num *= multiplier

            return num

        return float(num_str) if num_str.isdigit() else 0

    def _extract_year(self, text: str) -> Optional[int]:
        """从文本中提取年份"""
        year_match = re.search(r'20\d{2}', text)
        if year_match:
            return int(year_match.group())
        return None

    def _extract_quarter(self, text: str) -> Optional[int]:
        """从文本中提取季度"""
        quarter_match = re.search(r'(第)?([一二三四1234])[季度Qq]', text)
        if quarter_match:
            quarter_map = {'一': 1, '二': 2, '三': 3, '四': 4}
            q_str = quarter_match.group(2)
            if q_str in quarter_map:
                return quarter_map[q_str]
            elif q_str.isdigit():
                return int(q_str)
        return None

    def _get_metric_display_name(self, metric_name: str) -> str:
        """获取指标的显示名称"""
        display_names = {
            'profit_margin': '利润率',
            'return_on_assets': '资产回报率',
            'debt_to_equity': '债务权益比',
            'current_ratio': '流动比率',
            'revenue_growth': '收入增长率',
            'profit_growth': '利润增长率',
        }
        return display_names.get(metric_name, metric_name)

    def _format_metric_value(self, metric_name: str, value: float) -> str:
        """格式化指标值"""
        # 对于比率类指标，显示为百分比
        if metric_name in ['profit_margin', 'return_on_assets', 'revenue_growth', 'profit_growth']:
            return f"{value:.2%}"
        # 对于其他指标，保留两位小数
        else:
            return f"{value:.2f}"


# 创建全局实例供外部使用
financial_analyzer = FinancialAnalyzer()
