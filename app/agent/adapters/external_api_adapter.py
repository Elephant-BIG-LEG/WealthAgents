"""
外部 API 适配器
支持对接第三方数据源 API（Wind、同花顺、通联数据等）
"""

from typing import Dict, Any, List, Optional
import requests
import time
import hashlib
import hmac
from . import BaseToolAdapter


class ExternalAPIAdapter(BaseToolAdapter):
    """
    外部 API 适配器

    提供统一的接口对接多个第三方金融数据服务商
    """

    name = "external_api_adapter"
    description = "外部 API 适配器，支持 Wind、同花顺、通联数据等多个第三方数据源"
    version = "1.0.0"
    supported_protocols = ["HTTP", "HTTPS", "WebSocket"]

    # 支持的第三方 API 配置
    API_PROVIDERS = {
        'wind': {
            'name': 'Wind 资讯',
            'base_url': 'https://api.wind.com.cn/',
            'auth_type': 'api_key',
            'rate_limit': 100  # 每分钟请求数限制
        },
        'ths': {
            'name': '同花顺',
            'base_url': 'http://data.10jqka.com.cn/',
            'auth_type': 'token',
            'rate_limit': 60
        },
        'datayes': {
            'name': '通联数据',
            'base_url': 'https://api.datayes.com/',
            'auth_type': 'bearer',
            'rate_limit': 200
        }
    }

    def __init__(self):
        super().__init__()
        self.connected = False
        self.current_provider = None
        self.api_key = None
        self.session = requests.Session()
        self.request_count = 0
        self.last_request_time = 0

    def connect(self, provider: str, api_key: str, **kwargs) -> bool:
        """
        连接到第三方 API

        Args:
            provider: 服务提供商 (wind/ths/datayes)
            api_key: API 密钥
            **kwargs: 其他认证参数

        Returns:
            是否连接成功
        """
        try:
            if provider not in self.API_PROVIDERS:
                self.logger.error(f"不支持的 API 提供商：{provider}")
                return False

            self.current_provider = self.API_PROVIDERS[provider]
            self.api_key = api_key

            # 设置认证头
            self._setup_auth_headers(api_key, kwargs)

            self._log_operation(
                "connect", f"连接到 {self.current_provider['name']}")

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
        self.current_provider = None
        self.api_key = None
        self.session.close()
        self._log_operation("disconnect", "已断开连接")

    def fetch_data(self, query: str, **params) -> Dict[str, Any]:
        """
        从第三方 API 获取数据

        Args:
            query: 查询内容
            **params: API 特定参数

        Returns:
            获取的数据
        """
        if not self.connected:
            self.logger.error("未连接到 API 提供商")
            return {"error": "未连接"}

        # 检查速率限制
        if not self._check_rate_limit():
            self.logger.warning("超过速率限制")
            return {"error": "Rate limit exceeded"}

        api_type = params.get('api_type', 'market')

        # 根据 API 类型选择不同的请求方法
        if api_type == 'market':
            return self._fetch_market_data(query, params)
        elif api_type == 'financial':
            return self._fetch_financial_data(query, params)
        elif api_type == 'news':
            return self._fetch_news_data(query, params)
        else:
            return self._fetch_market_data(query, params)

    def transform_data(self, raw_data: Any) -> Dict[str, Any]:
        """
        转换 API 返回数据为标准格式

        Args:
            raw_data: API 返回的原始数据

        Returns:
            标准化后的数据
        """
        if not raw_data:
            return {
                "status": "error",
                "data": None,
                "message": "原始数据为空"
            }

        try:
            # 通用标准格式
            standardized = {
                "data": raw_data.get('data', raw_data),
                "source": self.current_provider['name'] if self.current_provider else 'unknown',
                "timestamp": raw_data.get('timestamp', time.strftime('%Y-%m-%d %H:%M:%S')),
                "request_id": raw_data.get('request_id', ''),
                "status_code": raw_data.get('code', 200)
            }

            return {
                "status": "success" if standardized['status_code'] == 200 else "error",
                "data": standardized,
                "metadata": {
                    "adapter_name": self.name,
                    "adapter_version": self.version,
                    "provider": self.current_provider['name'] if self.current_provider else None,
                    "transform_time": time.time()
                }
            }

        except Exception as e:
            self.logger.error(f"API 数据转换失败：{str(e)}")
            return {
                "status": "error",
                "data": None,
                "message": f"数据转换失败：{str(e)}"
            }

    def validate_connection(self) -> bool:
        """验证连接状态"""
        return self.connected and self.current_provider is not None

    def get_status(self) -> Dict[str, Any]:
        """获取适配器状态"""
        status = super().get_status()
        status.update({
            "current_provider": self.current_provider['name'] if self.current_provider else None,
            "request_count": self.request_count,
            "api_key_set": self.api_key is not None
        })
        return status

    # ==================== 内部方法 ====================

    def _setup_auth_headers(self, api_key: str, kwargs: dict):
        """
        设置认证头

        Args:
            api_key: API 密钥
            kwargs: 其他认证参数
        """
        auth_type = self.current_provider['auth_type']

        if auth_type == 'api_key':
            self.session.headers.update({'X-API-Key': api_key})
        elif auth_type == 'token':
            self.session.headers.update({'Authorization': f'Token {api_key}'})
        elif auth_type == 'bearer':
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

        # 添加自定义认证参数
        for key, value in kwargs.items():
            if key.startswith('auth_'):
                self.session.headers[key.replace(
                    'auth_', 'X-').title()] = value

    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            # 发送测试请求
            test_url = f"{self.current_provider['base_url']}api/health"
            response = self.session.get(test_url, timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败：{str(e)}")
            return False

    def _check_rate_limit(self) -> bool:
        """
        检查速率限制

        Returns:
            是否未超过限制
        """
        current_time = time.time()
        rate_limit = self.current_provider['rate_limit']

        # 如果距离上次请求不到 1 秒，计数
        if current_time - self.last_request_time < 60:
            if self.request_count >= rate_limit:
                return False
            self.request_count += 1
        else:
            # 重置计数器
            self.request_count = 1

        self.last_request_time = current_time
        return True

    def _generate_signature(self, params: dict) -> str:
        """
        生成请求签名

        Args:
            params: 请求参数

        Returns:
            签名字符串
        """
        sorted_params = sorted(params.items())
        sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
        signature = hmac.new(
            self.api_key.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _fetch_market_data(self, symbol: str, params: dict) -> Dict[str, Any]:
        """获取市场行情数据"""
        try:
            # TODO: 实现真实的 API 调用
            # 这里先返回模拟数据

            mock_data = {
                'symbol': symbol,
                'price': 100.50,
                'change': 2.5,
                'volume': 1000000,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'source': self.current_provider['name']
            }

            self._log_operation("fetch_market", f"获取 {symbol} 的行情数据")
            return mock_data

        except Exception as e:
            self.logger.error(f"获取行情数据失败：{str(e)}")
            return {"error": str(e)}

    def _fetch_financial_data(self, company_code: str, params: dict) -> Dict[str, Any]:
        """获取财务数据"""
        try:
            # TODO: 实现真实的 API 调用
            self.logger.info("财务数据 API 调用功能待实现")
            return {"error": "功能待实现"}

        except Exception as e:
            self.logger.error(f"获取财务数据失败：{str(e)}")
            return {"error": str(e)}

    def _fetch_news_data(self, keyword: str, params: dict) -> Dict[str, Any]:
        """获取新闻数据"""
        try:
            # TODO: 实现真实的 API 调用
            self.logger.info("新闻数据 API 调用功能待实现")
            return {"error": "功能待实现"}

        except Exception as e:
            self.logger.error(f"获取新闻数据失败：{str(e)}")
            return {"error": str(e)}
