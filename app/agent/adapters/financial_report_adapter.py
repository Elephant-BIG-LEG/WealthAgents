"""
财报数据适配器
支持从多个数据源获取上市公司财务报表数据
"""

from typing import Dict, Any, List, Optional
import requests
import time
from . import BaseToolAdapter


class FinancialReportAdapter(BaseToolAdapter):
    """
    财报数据适配器

    支持从巨潮资讯网、东方财富等获取上市公司财报数据
    """

    name = "financial_report_adapter"
    description = "财报数据适配器，支持获取上市公司年报、季报等财务数据"
    version = "1.0.0"
    supported_protocols = ["HTTP", "HTTPS"]

    # 支持的数据源
    DATA_SOURCES = {
        'cninfo': {
            'name': '巨潮资讯',
            'base_url': 'http://www.cninfo.com.cn/',
            'api_type': 'official'
        },
        'eastmoney': {
            'name': '东方财富',
            'base_url': 'https://datacenter.eastmoney.com/',
            'api_type': 'aggregated'
        }
    }

    def __init__(self):
        super().__init__()
        self.connected = False
        self.current_source = None
        self.session = requests.Session()

        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*'
        }

    def connect(self, source: str = 'eastmoney', **kwargs) -> bool:
        """
        连接到指定数据源

        Args:
            source: 数据源名称
            **kwargs: 其他参数

        Returns:
            是否连接成功
        """
        try:
            if source not in self.DATA_SOURCES:
                self.logger.error(f"不支持的数据源：{source}")
                return False

            self.current_source = self.DATA_SOURCES[source]
            self._log_operation(
                "connect", f"连接到 {self.current_source['name']}")

            # 测试连接
            test_result = self._test_connection()
            self.connected = test_result

            return test_result

        except Exception as e:
            self.logger.error(f"连接失败：{str(e)}")
            return False

    def disconnect(self):
        """断开连接"""
        self.connected = False
        self.current_source = None
        self.session.close()
        self._log_operation("disconnect", "已断开连接")

    def fetch_data(self, query: str, **params) -> Dict[str, Any]:
        """
        获取财报数据

        Args:
            query: 公司代码或名称
            **params: 其他参数（year, report_type 等）

        Returns:
            财报数据
        """
        if not self.connected:
            self.connect()

        data_source = params.get('data_source', 'eastmoney')
        year = params.get('year')
        report_type = params.get('report_type', 'annual')  # annual/quarterly

        if data_source == 'eastmoney':
            return self._fetch_eastmoney_report(query, year, report_type)
        elif data_source == 'cninfo':
            return self._fetch_cninfo_report(query, year, report_type)
        else:
            return self._fetch_eastmoney_report(query, year, report_type)

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """
        转换财报数据为标准格式

        Args:
            raw_data: 原始财报数据

        Returns:
            标准化后的财报数据
        """
        if not raw_data:
            return {
                "status": "error",
                "data": None,
                "message": "原始数据为空"
            }

        try:
            # 标准财报数据格式
            standardized = {
                "company_code": raw_data.get('company_code', ''),
                "company_name": raw_data.get('company_name', ''),
                "report_date": raw_data.get('report_date', ''),
                "report_type": raw_data.get('report_type', 'annual'),

                # 主要财务指标
                "revenue": float(raw_data.get('revenue', 0)),  # 营业收入
                "net_profit": float(raw_data.get('net_profit', 0)),  # 净利润
                "total_assets": float(raw_data.get('total_assets', 0)),  # 总资产
                # 总负债
                "total_liabilities": float(raw_data.get('total_liabilities', 0)),
                "equity": float(raw_data.get('equity', 0)),  # 净资产
                # 经营现金流
                "operating_cash_flow": float(raw_data.get('operating_cash_flow', 0)),

                # 增长率
                # 营收增长率
                "revenue_growth": float(raw_data.get('revenue_growth', 0)),
                # 利润增长率
                "profit_growth": float(raw_data.get('profit_growth', 0)),

                # 盈利能力
                "gross_margin": float(raw_data.get('gross_margin', 0)),  # 毛利率
                "net_margin": float(raw_data.get('net_margin', 0)),  # 净利率
                "roe": float(raw_data.get('roe', 0)),  # ROE

                # 数据来源
                "data_source": raw_data.get('source', 'unknown')
            }

            return {
                "status": "success",
                "data": standardized,
                "metadata": {
                    "adapter_name": self.name,
                    "adapter_version": self.version,
                    "transform_time": time.time(),
                    "data_completeness": self._calculate_completeness(standardized)
                }
            }

        except Exception as e:
            self.logger.error(f"财报数据转换失败：{str(e)}")
            return {
                "status": "error",
                "data": None,
                "message": f"数据转换失败：{str(e)}"
            }

    def validate_connection(self) -> bool:
        """验证连接是否有效"""
        return self.connected and self.current_source is not None

    def _calculate_completeness(self, data: dict) -> float:
        """计算数据完整性（0-1）"""
        if not data:
            return 0.0

        total_fields = len(data)
        non_null_fields = sum(1 for v in data.values()
                              if v is not None and v != 0)

        return round(non_null_fields / total_fields, 2) if total_fields > 0 else 0.0

    # ==================== 内部方法 ====================

    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            response = self.session.get(
                self.current_source['base_url'],
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败：{str(e)}")
            return False

    def _fetch_eastmoney_report(self, company_code: str, year: Optional[int], report_type: str) -> Dict[str, Any]:
        """从东方财富获取财报数据"""
        try:
            # TODO: 实现真实的 API 调用
            # 这里先返回模拟数据用于测试

            mock_data = {
                'company_code': company_code,
                'company_name': '测试公司',
                'report_date': f'{year}-12-31' if year else '2023-12-31',
                'report_type': report_type,
                'revenue': 10000000000,
                'net_profit': 2000000000,
                'total_assets': 50000000000,
                'total_liabilities': 30000000000,
                'equity': 20000000000,
                'operating_cash_flow': 3000000000,
                'revenue_growth': 0.15,
                'profit_growth': 0.20,
                'gross_margin': 0.35,
                'net_margin': 0.20,
                'roe': 0.10,
                'source': 'eastmoney'
            }

            self._log_operation("fetch_report", f"获取 {company_code} 的财报数据")
            return mock_data

        except Exception as e:
            self.logger.error(f"获取东方财富财报数据失败：{str(e)}")
            return {"error": str(e)}

    def _fetch_cninfo_report(self, company_code: str, year: Optional[int], report_type: str) -> Dict[str, Any]:
        """从巨潮资讯获取财报数据"""
        try:
            # TODO: 实现巨潮资讯 API 调用
            self.logger.info("巨潮资讯数据获取功能待实现")
            return {"error": "功能待实现"}

        except Exception as e:
            self.logger.error(f"获取巨潮资讯财报数据失败：{str(e)}")
            return {"error": str(e)}
