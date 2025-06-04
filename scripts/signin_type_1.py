#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名：signin_type_1.py
描述：自动化签到脚本，支持多个微信小程序的自动登录和签到功能
      已知支持的应用：
      1. LaLa station
      2. 鑫耀光环
作者：herryfish
创建日期：2024-03-17
最后修改：2025-05-24
"""

import json
import requests
from loguru import logger
import os
import time
from datetime import datetime
import hashlib
import sys

# 将项目根目录添加到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.notify_utils import load_send
from utils.config import get_app_configs, get_user_infos

APP = 'signin_type_1'

class AppBase:
    """微信小程序自动签到基础类。

    由于小程序会使用(Content-Encoding: br)brotli压缩，
    因此需要在python环境中导入brotli包。

    Attributes:
        app_name: 应用名称
        app_config: 应用配置信息
        comm_headers: 通用请求头
    """

    wx_mini_app_user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/122.0.0.0 Safari/537.36 '
                             'MicroMessenger/7.0.20.1781(0x6700143B) '
                             'NetType/WIFI MiniProgramEnv/Windows '
                             'WindowsWechat/WMPF WindowsWechat(0x63090c0f)'
                             'XWEB/11159')

    app_id = 'api.app.member'
    request_id = 'v5.app.member.wechat'

    def _login_jsontostr(self, base_params: dict, extra_params: dict) -> str:
        """将登录参数转换为签名字符串。

        Args:
            base_params (dict): 基础参数字典，包含app_id、app_time和app_secret等
            extra_params (dict): 额外参数字典，包含requestId、openId等

        Returns:
            str: 将所有参数按键名排序后拼接的字符串，格式为"key1=value1&key2=value2"
        """

        params_list = []
        for key, value in base_params.items():
            params_list.append(f"{key}={value}")

        for key, value in extra_params.items():
            value_str = json.dumps(value) if isinstance(value, (dict, list)) else str(value)
            if value_str == "null":
                params_list.append(f"{key}={value}")
            else:
                params_list.append(f"{key}={value_str}")

        return "&".join(sorted(params_list))

    def __init__(self, app_name: str, open_id: str):
        """初始化应用实例。

        Args:
            app_name: 应用名称
            open_id: 用户的OpenID
        """
        self.app_name = app_name
        self.open_id = open_id
        self.app_config = get_app_configs(APP).get(app_name, {})
        self.comm_headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': self.wx_mini_app_user_agent,
            'Content-Type': 'application/json'
        }
        self.login_url = f"https://{self.app_config['host']}/api/Token/WXVIPLogin"
        self.signin_url = f"https://{self.app_config['host']}/api/Sign/SignIn"

    def login(self, openid: str) -> str:
        """执行登录操作。

        Args:
            openid: 用户的OpenID

        Returns:
            str: 成功返回访问令牌，失败返回None
        """
        formatted_time = datetime.now().strftime('%Y%m%d%H%M%S')
        json_data = {
            "requestId": self.request_id,
            "openId": openid
        }

        base_data = {
            'app_id': self.app_id,
            'app_time': formatted_time,
            'app_secret': self.app_config['app_secret']
        }

        str_data = self._login_jsontostr(base_data, json_data)

        md5_hash = hashlib.md5()
        md5_hash.update(str_data.encode('utf-8'))
        md5_result = md5_hash.hexdigest().upper()

        self.comm_headers.update({
            'app_time': formatted_time,
            'app_id': self.app_id,
            'app_sign': md5_result
        })

        try:
            response = requests.post(self.login_url,
                                   json=json_data,
                                   headers=self.comm_headers)
            response.raise_for_status()

            result = response.json()
            logger.info(f"{self.app_name} 登录请求结果: {result}")
            if not result['success']:
                load_send(self.app_name, response.text)
                logger.error(f"{self.app_name}: {response.content}")
                return None
            return result['data']['accesstoken']

        except requests.exceptions.RequestException as e:
            load_send(self.app_name, f'请求异常: {str(e)}')
            logger.error(f"{self.app_name} 登录请求失败: {str(e)}")
            return None

    def signin(self, token: str) -> None:
        """执行签到操作。

        Args:
            token: 访问令牌
        """
        self.comm_headers['Authorization'] = token
        self.comm_headers['Host'] = self.app_config['host']
        headers = {**self.comm_headers, **self.app_config['headers']}

        try:
            response = requests.post(self.signin_url, headers=headers)
            response.raise_for_status()

            result = response.json()
            logger.info(f"{self.app_name} 签到请求结果: {result}")
            if not result['success']:
                # 解码错误信息中的字节字符串
                error_msg = result.get('msg', '')
                if isinstance(error_msg, bytes):
                    error_msg = error_msg.decode('utf-8')
                result['msg'] = error_msg
                load_send(self.app_name, json.dumps(result, ensure_ascii=False))
                logger.error(f"{self.app_name}: {json.dumps(result, ensure_ascii=False)}")
            else:
                logger.info(f"{self.app_name}: 签到成功")

        except requests.exceptions.RequestException as e:
            load_send(self.app_name, f'签到请求异常: {str(e)}')
            logger.error(f"{self.app_name} 签到请求失败: {str(e)}")

    def main(self) -> None:
        """执行登录和签到操作。"""
        token = self.login(self.open_id)
        if token:
            time.sleep(2)
            self.signin(f"Bearer {token}")  # 注意这里的 token 应该是 "Bearer {token}" 的形式
        else:
            logger.error(f"{self.app_name}: 登录失败")

if __name__ == '__main__':
    """主函数，执行自动登录和签到流程。"""
    accounts = get_user_infos(APP)
    if not accounts:
        logger.error("未找到有效的账户配置信息")
        exit(1)

    for account in accounts:
        AppBase(account['app'], account['openid']).main()
        time.sleep(1)
