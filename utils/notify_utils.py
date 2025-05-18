#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名：notify_utils.py
描述：消息推送工具函数
作者：herryfish
创建日期：2024-03-17
最后修改：2024-03-17
"""

from loguru import logger

def load_send(title: str, content: str) -> None:
    """加载并执行消息推送功能。

    Args:
        title: 消息标题
        content: 消息内容

    Returns:
        None

    Raises:
        ImportError: 当notify模块导入失败时抛出
        Exception: 当消息推送失败时抛出
    """
    logger.info("加载推送功能中...")
    try:
        from notify import send
        send(title, content)
        logger.info("消息推送成功")
    except ImportError as e:
        logger.error(f"❌导入notify模块失败: {str(e)}")
    except Exception as e:
        logger.error(f"❌消息推送失败: {str(e)}")
        raise