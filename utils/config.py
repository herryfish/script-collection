#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名：config.py
描述：配置加载模块，用于读取和管理应用配置
作者：herryfish
创建日期：2024-03-17
最后修改：2024-03-17
"""

import os
import abc
import yaml
import re
from loguru import logger
from typing import Dict, List, Optional, Any, Type

class ConfigSourceBase(abc.ABC):
    """配置源抽象基类，定义配置加载的接口。
    
    所有配置源实现都应继承此类并实现其抽象方法。
    """
    
    @abc.abstractmethod
    def load_config(self) -> dict:
        """加载配置数据的抽象方法。
        
        Returns:
            dict: 配置数据字典
        """
        pass

class YamlConfigSource(ConfigSourceBase):
    """YAML配置源实现类。
    
    从YAML文件加载配置数据。
    
    Attributes:
        config_path: YAML配置文件的路径
    """
    
    def __init__(self, config_path: str):
        """初始化YAML配置源。
        
        Args:
            config_path: YAML配置文件的路径
        """
        self.config_path = config_path
    
    def load_config(self) -> dict:
        """从YAML文件加载配置数据。
        
        Returns:
            dict: 配置数据字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载YAML配置文件失败: {str(e)}")
            return {}

class EnvironmentConfigSource(ConfigSourceBase):
    """环境变量配置源实现类。
    
    从系统环境变量加载配置数据。
    支持通过特定前缀和分隔符解析嵌套结构。
    
    Attributes:
        prefix: 环境变量前缀，用于筛选相关环境变量
        separator: 环境变量名称中的分隔符，用于解析嵌套结构
    """
    
    def __init__(self, prefix: str = "", separator: str = "__"):
        """初始化环境变量配置源。
        
        Args:
            prefix: 环境变量前缀，只加载以此前缀开头的环境变量，默认为空字符串（加载所有环境变量）
            separator: 环境变量名称中的分隔符，用于解析嵌套结构，默认为双下划线
        """
        self.prefix = prefix
        self.separator = separator
    
    def load_config(self) -> dict:
        """从环境变量加载配置数据。
        
        将环境变量转换为嵌套的配置字典。例如：
        环境变量 APP_CONFIG__DATABASE__HOST=localhost 将被转换为：
        {"app_config": {"database": {"host": "localhost"}}}
        
        Returns:
            dict: 配置数据字典
        """
        try:
            config = {}
            pattern = re.compile(f"^{self.prefix}") if self.prefix else None
            
            for key, value in os.environ.items():
                # 如果设置了前缀，则只处理匹配前缀的环境变量
                if pattern and not pattern.match(key):
                    continue
                
                # 移除前缀
                if self.prefix:
                    key = pattern.sub("", key)
                
                # 转换为小写并分割键名
                key = key.lower()
                parts = key.split(self.separator)
                
                # 递归设置嵌套值
                current = config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            
            return config
        except Exception as e:
            logger.error(f"加载环境变量配置失败: {str(e)}")
            return {}

class ConfigLoader:
    """配置加载器，用于管理和访问配置数据。
    
    支持从不同配置源加载配置数据，并提供统一的访问接口。
    """
    
    def __init__(self, config_source: Optional[ConfigSourceBase] = None):
        """初始化配置加载器。
        
        Args:
            config_source: 配置源对象，如果为None则使用默认的YAML配置源
        """
        if config_source is None:
            # 默认使用YAML配置源
            default_config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'app_config.yaml')
            config_source = YamlConfigSource(default_config_path)
            
        self.config_source = config_source
        self.config_data = self._load_config()
    
    def _load_config(self) -> dict:
        """加载配置数据。

        Returns:
            dict: 配置数据字典
        """
        return self.config_source.load_config()
    
    def get_app_configs(self) -> Dict[str, Any]:
        """获取应用配置数据。
        
        Returns:
            Dict[str, Any]: 应用配置数据字典
        """
        return self.config_data.get('app_configs', {})
    
    def get_user_infos(self, app_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取用户信息数据。
        
        Args:
            app_name: 应用名称，如果提供则只返回该应用的用户信息
            
        Returns:
            List[Dict[str, Any]]: 用户信息数据列表
        """
        user_infos = self.config_data.get('user_infos', [])
        if app_name:
            return [user for user in user_infos if user.get('app') == app_name]
        return user_infos
    
    def get_common_settings(self, key: Optional[str] = None) -> Any:
        """获取通用设置数据。
        
        Args:
            key: 设置键名，如果为None则返回所有通用设置
            
        Returns:
            Any: 通用设置数据
        """
        common_settings = self.config_data.get('common', {})
        return common_settings.get(key) if key else common_settings

def set_config_source(config_source: ConfigSourceBase) -> None:
    """设置全局配置加载器的配置源。
    
    可用于在运行时切换配置源。
    
    Args:
        config_source: 新的配置源对象
    """
    global config_loader
    config_loader = ConfigLoader(config_source)

# 创建全局配置加载器实例
config_loader = ConfigLoader()

# 导出便捷函数
def get_app_configs() -> Dict[str, Any]:
    """获取应用配置数据的便捷函数。
    
    Returns:
        Dict[str, Any]: 应用配置数据字典
    """
    return config_loader.get_app_configs()

def get_user_infos(app_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取用户信息数据的便捷函数。
    
    Args:
        app_name: 应用名称，如果提供则只返回该应用的用户信息
        
    Returns:
        List[Dict[str, Any]]: 用户信息数据列表
    """
    return config_loader.get_user_infos(app_name)

def get_common_settings(key: Optional[str] = None) -> Any:
    """获取通用设置数据的便捷函数。
    
    Args:
        key: 设置键名，如果为None则返回所有通用设置
        
    Returns:
        Any: 通用设置数据
    """
    return config_loader.get_common_settings(key)