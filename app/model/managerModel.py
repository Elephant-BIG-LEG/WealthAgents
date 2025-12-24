#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
大模型管理器模块
用于封装大模型的创建、配置和管理操作
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, TypeVar, Generic, Union
import json
import yaml
from dotenv import load_dotenv

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ModelConfig:
    """
    模型配置类，用于存储和管理模型的配置参数
    """
    def __init__(self, model_name: str, **kwargs):
        """
        初始化模型配置
        
        Args:
            model_name: 模型名称
            **kwargs: 其他配置参数
        """
        self.model_name = model_name
        self.parameters = kwargs
        
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置参数
        
        Args:
            key: 参数名称
            default: 默认值
            
        Returns:
            配置参数值或默认值
        """
        return self.parameters.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置参数
        
        Args:
            key: 参数名称
            value: 参数值
        """
        self.parameters[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            配置字典
        """
        return {"model_name": self.model_name, **self.parameters}


class ModelManager:
    """
    模型管理器基类
    提供模型创建、配置和管理的基础功能
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        初始化模型管理器
        """
        if not hasattr(self, 'models'):
            self.models = {}
            self.default_model = None
            self.configs = {}
            logger.info("模型管理器初始化完成")
    
    def create_model(self, config: ModelConfig) -> Any:
        """
        创建模型实例
        需要子类实现具体的模型创建逻辑
        
        Args:
            config: 模型配置
            
        Returns:
            模型实例
        
        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现create_model方法")
    
    def get_model(self, model_name: Optional[str] = None) -> Any:
        """
        获取模型实例
        
        Args:
            model_name: 模型名称，如果为None则返回默认模型
            
        Returns:
            模型实例
            
        Raises:
            ValueError: 模型不存在
        """
        if model_name is None:
            if self.default_model is None:
                raise ValueError("未设置默认模型")
            model_name = self.default_model
        
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        return self.models[model_name]
    
    def register_model(self, model_name: str, model: Any, set_default: bool = False) -> None:
        """
        注册模型实例
        
        Args:
            model_name: 模型名称
            model: 模型实例
            set_default: 是否设置为默认模型
        """
        self.models[model_name] = model
        if set_default or len(self.models) == 1:
            self.default_model = model_name
        logger.info(f"模型 {model_name} 注册完成")
    
    def unregister_model(self, model_name: str) -> None:
        """
        注销模型实例
        
        Args:
            model_name: 模型名称
            
        Raises:
            ValueError: 模型不存在
        """
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        del self.models[model_name]
        if self.default_model == model_name:
            self.default_model = next(iter(self.models.keys()), None)
        logger.info(f"模型 {model_name} 注销完成")
    
    def set_default_model(self, model_name: str) -> None:
        """
        设置默认模型
        
        Args:
            model_name: 模型名称
            
        Raises:
            ValueError: 模型不存在
        """
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        self.default_model = model_name
        logger.info(f"默认模型设置为 {model_name}")
    
    def list_models(self) -> list:
        """
        列出所有注册的模型
        
        Returns:
            模型名称列表
        """
        return list(self.models.keys())


class ModelFactory:
    """
    模型工厂类，用于创建不同类型的模型实例
    """
    _model_creators = {}
    
    @classmethod
    def register_creator(cls, model_type: str, creator_func) -> None:
        """
        注册模型创建器函数
        
        Args:
            model_type: 模型类型
            creator_func: 创建模型的函数
        """
        cls._model_creators[model_type] = creator_func
        logger.info(f"模型创建器 {model_type} 注册完成")
    
    @classmethod
    def unregister_creator(cls, model_type: str) -> None:
        """
        注销模型创建器函数
        
        Args:
            model_type: 模型类型
        """
        if model_type in cls._model_creators:
            del cls._model_creators[model_type]
            logger.info(f"模型创建器 {model_type} 注销完成")
    
    @classmethod
    def create(cls, model_type: str, **kwargs) -> Any:
        """
        创建模型实例
        
        Args:
            model_type: 模型类型
            **kwargs: 创建参数
            
        Returns:
            模型实例
            
        Raises:
            ValueError: 模型类型不存在
        """
        if model_type not in cls._model_creators:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        try:
            return cls._model_creators[model_type](**kwargs)
        except Exception as e:
            logger.error(f"创建模型 {model_type} 失败: {str(e)}")
            raise


class EnhancedModelManager(ModelManager):
    """
    增强的模型管理器
    集成了模型工厂功能
    """
    
    def __init__(self):
        """
        初始化增强模型管理器
        """
        super(EnhancedModelManager, self).__init__()
        self.model_factory = ModelFactory()
        logger.info("增强模型管理器初始化完成")
    
    def create_model(self, config: ModelConfig) -> Any:
        """
        使用配置创建模型
        
        Args:
            config: 模型配置
            
        Returns:
            模型实例
        """
        model_type = config.get('type', 'default')
        model_params = config.to_dict()
        
        try:
            # 使用工厂创建模型
            model = self.model_factory.create(model_type, **model_params)
            
            # 缓存配置
            self.configs[config.model_name] = config
            
            # 注册模型
            self.register_model(config.model_name, model)
            
            logger.info(f"成功创建并注册模型: {config.model_name}")
            return model
        except Exception as e:
            logger.error(f"创建模型 {config.model_name} 失败: {str(e)}")
            raise
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """
        获取模型配置
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型配置，如果不存在则返回None
        """
        return self.configs.get(model_name)
    
    def update_model_config(self, model_name: str, **kwargs) -> None:
        """
        更新模型配置
        
        Args:
            model_name: 模型名称
            **kwargs: 新的配置参数
            
        Raises:
            ValueError: 模型不存在
        """
        if model_name not in self.models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        if model_name not in self.configs:
            self.configs[model_name] = ModelConfig(model_name)
        
        for key, value in kwargs.items():
            self.configs[model_name].set(key, value)
        
        logger.info(f"模型配置 {model_name} 更新完成")
    
    def reload_model(self, model_name: str) -> Any:
        """
        重新加载模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            新的模型实例
            
        Raises:
            ValueError: 模型不存在或配置不存在
        """
        if model_name not in self.configs:
            raise ValueError(f"模型配置 {model_name} 不存在")
        
        # 保存默认设置
        was_default = self.default_model == model_name
        
        # 创建新模型
        new_model = self.create_model(self.configs[model_name].__class__(**self.configs[model_name].to_dict()))
        
        # 恢复默认设置
        if was_default:
            self.set_default_model(model_name)
        
        logger.info(f"模型 {model_name} 重新加载完成")
        return new_model
    
    def batch_create_models(self, config_list: list) -> Dict[str, Any]:
        """
        批量创建模型
        
        Args:
            config_list: 配置列表
            
        Returns:
            模型实例字典
        """
        results = {}
        for config in config_list:
            try:
                if isinstance(config, dict):
                    config_obj = ModelConfig(**config)
                elif isinstance(config, ModelConfig):
                    config_obj = config
                else:
                    raise ValueError("配置必须是字典或ModelConfig对象")
                    
                model = self.create_model(config_obj)
                results[config_obj.model_name] = model
            except Exception as e:
                logger.error(f"批量创建模型失败: {str(e)}")
                results[config_obj.model_name] = None
        
        return results


class ConfigLoader:
    """
    配置加载器类
    支持从环境变量、配置文件加载配置
    """
    
    def __init__(self, env_file: str = '.env'):
        """
        初始化配置加载器
        
        Args:
            env_file: 环境变量文件路径
        """
        self.env_file = env_file
        self.config_cache = {}
        
        # 尝试加载.env文件
        try:
            load_dotenv(env_file)
            logger.info(f"成功加载环境变量文件: {env_file}")
        except Exception as e:
            logger.warning(f"加载环境变量文件失败: {str(e)}")
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """
        获取环境变量
        
        Args:
            key: 环境变量名称
            default: 默认值
            
        Returns:
            环境变量值或默认值
        """
        return os.environ.get(key, default)
    
    def get_env_int(self, key: str, default: int = 0) -> int:
        """
        获取整型环境变量
        
        Args:
            key: 环境变量名称
            default: 默认值
            
        Returns:
            整型环境变量值或默认值
        """
        value = self.get_env(key)
        if value is None:
            return default
        
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_env_bool(self, key: str, default: bool = False) -> bool:
        """
        获取布尔型环境变量
        
        Args:
            key: 环境变量名称
            default: 默认值
            
        Returns:
            布尔型环境变量值或默认值
        """
        value = self.get_env(key)
        if value is None:
            return default
        
        if isinstance(value, bool):
            return value
        
        value = value.lower()
        if value in ('true', 't', 'yes', 'y', '1'):
            return True
        elif value in ('false', 'f', 'no', 'n', '0'):
            return False
        return default
    
    def load_json_config(self, config_file: str) -> Dict[str, Any]:
        """
        加载JSON配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        if config_file in self.config_cache:
            return self.config_cache[config_file]
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 缓存配置
            self.config_cache[config_file] = config
            logger.info(f"成功加载JSON配置文件: {config_file}")
            return config
        except Exception as e:
            logger.error(f"加载JSON配置文件失败 {config_file}: {str(e)}")
            return {}
    
    def load_yaml_config(self, config_file: str) -> Dict[str, Any]:
        """
        加载YAML配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        if config_file in self.config_cache:
            return self.config_cache[config_file]
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 缓存配置
            self.config_cache[config_file] = config or {}
            logger.info(f"成功加载YAML配置文件: {config_file}")
            return config or {}
        except ImportError:
            logger.error("缺少PyYAML库，请安装: pip install pyyaml")
            return {}
        except Exception as e:
            logger.error(f"加载YAML配置文件失败 {config_file}: {str(e)}")
            return {}
    
    def load_config(self, config_file: str) -> Dict[str, Any]:
        """
        根据文件扩展名自动加载配置文件
        
        Args:
            config_file: 配置文件路径
            
        Returns:
            配置字典
        """
        ext = os.path.splitext(config_file)[1].lower()
        
        if ext in ['.json']:
            return self.load_json_config(config_file)
        elif ext in ['.yaml', '.yml']:
            return self.load_yaml_config(config_file)
        else:
            logger.warning(f"不支持的配置文件格式: {ext}")
            return {}
    
    def get_model_config_from_env(self, model_name: str) -> Dict[str, Any]:
        """
        从环境变量获取模型配置
        环境变量格式: MODEL_{MODEL_NAME}_{CONFIG_KEY}
        
        Args:
            model_name: 模型名称
            
        Returns:
            模型配置字典
        """
        prefix = f"MODEL_{model_name.upper()}_"
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                config[config_key] = self._parse_env_value(value)
        
        if config:
            logger.info(f"从环境变量获取模型配置: {model_name}")
        
        return config
    
    def _parse_env_value(self, value: str) -> Any:
        """
        解析环境变量值
        
        Args:
            value: 环境变量字符串值
            
        Returns:
            解析后的值
        """
        # 尝试解析JSON
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except:
                pass
        
        # 尝试解析布尔值
        value_lower = value.lower()
        if value_lower == 'true':
            return True
        elif value_lower == 'false':
            return False
        elif value_lower == 'null' or value_lower == 'none':
            return None
        
        # 尝试解析数字
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except:
            pass
        
        return value


class ConfigurableModelManager(EnhancedModelManager):
    """
    可配置的模型管理器
    集成配置加载功能
    """
    
    def __init__(self, env_file: str = '.env'):
        """
        初始化可配置模型管理器
        
        Args:
            env_file: 环境变量文件路径
        """
        super(ConfigurableModelManager, self).__init__()
        self.config_loader = ConfigLoader(env_file)
        logger.info("可配置模型管理器初始化完成")
    
    def create_model_from_config(self, config_source: Union[str, Dict[str, Any]], model_name: Optional[str] = None) -> Any:
        """
        从配置源创建模型
        
        Args:
            config_source: 配置文件路径或配置字典
            model_name: 可选的模型名称，如果不提供则使用配置中的名称
            
        Returns:
            模型实例
        """
        # 加载配置
        if isinstance(config_source, str):
            # 从文件加载配置
            config = self.config_loader.load_config(config_source)
        else:
            # 直接使用配置字典
            config = config_source.copy()
        
        # 确定模型名称
        final_model_name = model_name or config.get('model_name')
        if not final_model_name:
            raise ValueError("必须提供模型名称")
        
        # 从环境变量获取覆盖配置
        env_config = self.config_loader.get_model_config_from_env(final_model_name)
        config.update(env_config)
        
        # 设置模型名称
        config['model_name'] = final_model_name
        
        # 创建配置对象
        model_config = ModelConfig(**config)
        
        # 创建模型
        return self.create_model(model_config)
    
    def load_models_from_config(self, config_file: str) -> Dict[str, Any]:
        """
        从配置文件批量加载模型
        
        Args:
            config_file: 包含多个模型配置的文件路径
            
        Returns:
            模型实例字典
        """
        config = self.config_loader.load_config(config_file)
        
        # 支持两种格式：models数组或直接的模型配置字典
        models_config = config.get('models', [])
        if not isinstance(models_config, list):
            # 如果不是数组，尝试作为单个模型配置处理
            models_config = [models_config]
        
        results = self.batch_create_models(models_config)
        logger.info(f"从配置文件加载了 {len(results)} 个模型")
        return results
    
    def get_config_value(self, key: str, default: Any = None, section: Optional[str] = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            section: 配置节
            
        Returns:
            配置值或默认值
        """
        if section:
            env_key = f"{section.upper()}_{key.upper()}"
        else:
            env_key = key.upper()
        
        return self.config_loader.get_env(env_key, default)


# 创建增强的全局模型管理器实例
global_configurable_model_manager = ConfigurableModelManager()
# 保持向后兼容
global_model_manager = global_configurable_model_manager

