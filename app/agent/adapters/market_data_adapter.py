"""
行情数据适配器
支持多种数据源的行情数据获取（新浪财经、东方财富、腾讯财经等）
"""

from typing import Dict, Any, List, Optional
import requests
import time
from . import BaseToolAdapter


class MarketDataAdapter(BaseToolAdapter):
    """
    行情数据适配器

    支持从多个数据源获取股票、基金等金融产品的实时和历史行情数据
    """

    name = "market_data_adapter"
    description = "行情数据适配器，支持多数据源获取实时和历史行情"
    version = "1.0.0"
    supported_protocols = ["HTTP", "HTTPS"]

    # 支持的数据源配置
    DATA_SOURCES = {
        'sina': {
            'name': '新浪财经',
            'base_url': 'https://hq.sinajs.cn/',
            'api_type': 'realtime'
        },
        'eastmoney': {
            'name': '东方财富',
            'base_url': 'http://push2.eastmoney.com/',
            'api_type': 'quote'
        },
        'qq': {
            'name': '腾讯财经',
            'base_url': 'http://qt.gtimg.cn/',
            'api_type': 'quote'
        }
    }

    def __init__(self):
        super().__init__()
        self.connected = False
        self.current_source = None
        self.session = requests.Session()

    def connect(self, source: str = 'sina', **kwargs) -> bool:
        """
        连接到指定数据源

        Args:
            source: 数据源名称 (sina/eastmoney/qq)
            **kwargs: 其他连接参数

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
        获取行情数据

        Args:
            query: 股票代码或名称
            **params: 其他参数（data_source, fields 等）

        Returns:
            行情数据
        """
        if not self.connected:
            self.logger.warning("未连接到数据源，尝试自动连接...")
            self.connect()

        data_source = params.get('data_source', 'sina')

        # 根据数据源选择不同的获取方法
        if data_source == 'sina':
            return self._fetch_sina_data(query, params)
        elif data_source == 'eastmoney':
            return self._fetch_eastmoney_data(query, params)
        elif data_source == 'qq':
            return self._fetch_qq_data(query, params)
        else:
            return self._fetch_sina_data(query, params)  # 默认使用新浪

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """
        转换行情数据为标准格式

        Args:
            raw_data: 原始行情数据

        Returns:
            标准化后的行情数据
        """
        if not raw_data:
            return {
                "status": "error",
                "data": None,
                "message": "原始数据为空"
            }

        try:
            # 标准格式转换
            standardized = {
                "symbol": raw_data.get('code', ''),
                "name": raw_data.get('name', ''),
                "current_price": float(raw_data.get('price', 0)),
                "open": float(raw_data.get('open', 0)),
                "high": float(raw_data.get('high', 0)),
                "low": float(raw_data.get('low', 0)),
                "close": float(raw_data.get('close', 0)),
                "volume": float(raw_data.get('volume', 0)),
                "amount": float(raw_data.get('amount', 0)),
                "change_percent": float(raw_data.get('change_percent', 0)),
                "change_amount": float(raw_data.get('change_amount', 0)),
                "timestamp": raw_data.get('timestamp', ''),
                "data_source": raw_data.get('source', 'unknown')
            }

            return {
                "status": "success",
                "data": standardized,
                "metadata": {
                    "adapter_name": self.name,
                    "adapter_version": self.version,
                    "transform_time": time.time()
                }
            }

        except Exception as e:
            self.logger.error(f"数据转换失败：{str(e)}")
            return {
                "status": "error",
                "data": None,
                "message": f"数据转换失败：{str(e)}"
            }

    def validate_connection(self) -> bool:
        """验证连接是否有效"""
        return self.connected and self.current_source is not None

    def get_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        status = super().get_status()
        status.update({
            "current_source": self.current_source['name'] if self.current_source else None,
            "session_active": self.session is not None
        })
        return status

    # ==================== 内部方法 ====================

    def _test_connection(self) -> bool:
        """测试连接是否正常"""
        try:
            response = self.session.get(
                self.current_source['base_url'],
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败：{str(e)}")
            return False

    def _fetch_sina_data(self, symbol: str, params: dict) -> Dict[str, Any]:
        """从新浪财经获取数据"""
        try:
            # 处理股票代码
            if symbol.startswith('6'):
                code = f"sh{symbol}"
            else:
                code = f"sz{symbol}"

            url = f"{self.current_source['base_url']}?list={code}"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # 解析新浪的返回数据
            content = response.text
            if '=' in content:
                parts = content.split('=')
                if len(parts) > 1:
                    data_str = parts[1].strip('"').split(',')

                    if len(data_str) >= 32:
                        raw_data = {
                            'code': symbol,
                            'name': data_str[0],
                            'open': float(data_str[1]),
                            'close': float(data_str[2]),
                            'current': float(data_str[3]),
                            'high': float(data_str[4]),
                            'low': float(data_str[5]),
                            'volume': float(data_str[8]),
                            'amount': float(data_str[9]),
                            'timestamp': f"{data_str[30]} {data_str[31]}",
                            'source': 'sina'
                        }

                        # 计算涨跌幅
                        if float(data_str[2]) != 0:
                            change_percent = (
                                float(data_str[3]) - float(data_str[2])) / float(data_str[2]) * 100
                            change_amount = float(
                                data_str[3]) - float(data_str[2])
                            raw_data['change_percent'] = round(
                                change_percent, 2)
                            raw_data['change_amount'] = round(change_amount, 2)

                        return raw_data

            return {"error": "无法解析新浪数据"}

        except Exception as e:
            self.logger.error(f"获取新浪数据失败：{str(e)}")
            return {"error": str(e)}

    def _fetch_eastmoney_data(self, symbol: str, params: dict) -> Dict[str, Any]:
        """从东方财富获取数据"""
        # TODO: 实现东方财富 API 调用
        self.logger.info("东方财富数据获取功能待实现")
        return {"error": "功能待实现"}

    def _fetch_qq_data(self, symbol: str, params: dict) -> Dict[str, Any]:
        """从腾讯财经获取数据"""
        # TODO: 实现腾讯财经 API 调用
        self.logger.info("腾讯财经数据获取功能待实现")
        return {"error": "功能待实现"}
