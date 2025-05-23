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
import yaml
from loguru import logger
from typing import Dict, List, Optional

class ConfigLoader:
    """配置加载类，用于读取和管理YAML配置文件。

    Attributes:
        config_path: YAML配置文件的路径
        config_data: 加载的配置数据
    """

    def __init__(self):
        """初始化配置加载器。"""
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'app_config.yaml')
        self.config_data = self._load_config()

    def _load_config(self) -> dict:
        """加载YAML配置文件。

        Returns:
            dict: 配置数据字典
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return {}

    def get_app_configs(self, app_name: str) -> Dict:
        """获取指定应用的配置信息。

        Args:
            app_name: 应用名称

        Returns:
            Dict: 应用配置字典
        """
        return self.config_data.get(app_name, {}).get('app_configs', {})

    def get_app_user_infos(self, app_name: str) -> List[Dict]:
        """获取指定应用的用户信息列表。

        Args:
            app_name: 应用名称

        Returns:
            List[Dict]: 用户信息列表
        """
        return self.config_data.get(app_name, {}).get('user_infos', [])

    def get_common_settings(self, key: str) -> List[Dict]:
        """获取指定项目的设定信息列表。

        Args:
            key: 项目名称

        Returns:
            List[Dict]: 设定信息列表
        """
        return self.config_data.get('common', {}).get(key, [])

# 创建全局配置加载器实例
config_loader = ConfigLoader()

def get_app_configs(app_name: str) -> Dict:
    """获取应用配置的便捷函数。

    Args:
        app_name: 应用名称

    Returns:
        Dict: 应用配置字典
    """
    return config_loader.get_app_configs(app_name)

def get_user_infos(app_name: str) -> List[Dict]:
    """获取用户信息的便捷函数。

    Args:
        app_name: 应用名称

    Returns:
        List[Dict]: 用户信息列表
    """
    return config_loader.get_app_user_infos(app_name)

def get_common_settings(key: str) -> List[Dict]:
    """获取设定信息的便捷函数。

    Args:
        key: 项目名称

    Returns:
        List[Dict]: 设定信息列表
    """
    return config_loader.get_common_settings(key)