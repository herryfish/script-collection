#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名：smzdm.py
描述：什么值得买自动签到、任务完成和抽奖脚本
作者：herryfish
创建日期：2025-01-01
最后修改：2025-06-08
"""
# 标准库
import base64
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime

# 第三方库
import requests
import urllib3
from loguru import logger

# 将项目根目录添加到 sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 本地应用/库
from utils.notify_utils import load_send
from utils.config import get_app_configs, get_user_infos
urllib3.disable_warnings()

# 配置日志输出
logger.remove()
logger.add(
    os.path.join(project_root, "logs", "smzdm_debug.log"),
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    encoding="utf-8"
)
logger.add(
    sys.stdout,
    level="DEBUG",
    filter=lambda record: record['level'].name != "DEBUG"
)

APP = 'smzdm'

def clean_html(html_string):
    """去除字符串中HTML标签"""
    pattern = re.compile(r'<[^>]+>')
    return pattern.sub('', html_string).strip()

def extract_and_decode_base64(input_str):
    """利用正则表达式找出单引号间的 Base64 编码字符串"""
    match = re.search(r"atob\('([^']*)'\)", input_str)
    if not match:
        raise ValueError('未找到 Base64 编码内容')
    
    encoded_data = match.group(1)  # 获取捕获的编码字符串
    
    try:
        # 执行 Base64 解码操作
        decoded_bytes = base64.b64decode(encoded_data)
        # 尝试以 UTF-8 编码将字节转换为字符串
        return decoded_bytes.decode('utf-8')
    except UnicodeDecodeError:
        # 若 UTF-8 解码失败，则返回原始字节数据的十六进制表示
        return decoded_bytes.hex()
    except base64.binascii.Error as e:
        raise ValueError(f'Base64 解码出错: {e}')

class SMZDM():
    """什么值得买"""

    topic_page_list = []
    lottery_list = []
    activity_list = []
    
    # 常量定义
    TIMEOUT = 10
    MAX_RETRIES = 3
    RETRY_DELAY = 2
    app_ver = '10.4.1'
    is_wx = '1'
    device = 'android'
    key = 'apr1$AwP!wRRT$gJ/q.X24poeBInlUJC'
    sk = 'ierkM0OZZbsuBKLoAgQ6OJneLMXBQXmzX+LXkNTuKch8Ui2jGlahuFyWIzBiDq/L' 
    headers = {
        "Host": "user-api.smzdm.com",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "smzdm_android_V10.4.1 rv:841 (22021211RC;Android12;zh)smzdmapp",
    }
    zhiyou_headers = {
        "origin": "https://m.smzdm.com",
        "x-requested-with": "com.smzdm.client.android",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148/smzdm 10.4.6 rv:130.1 (iPhone 13; iOS 15.6; zh_CN)/iphone_smzdmapp/10.4.6/wkwebview/jsbv_1.0.0",
        "Accept-Language": "zh-CN,zh-Hans;q=0.9",
        "Referer": "https://m.smzdm.com/",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def __init__(self, cookie: str):
        self.cookie = cookie
        self.headers['Cookie'] = self.cookie
        self.zhiyou_headers['Cookie'] = self.cookie

    def _request_with_retry(self, method: str, url: str, headers: dict, data: dict = None) -> requests.Response:
        """发送HTTP请求并处理重试逻辑
        
        该方法封装了HTTP请求的发送和重试逻辑，支持GET和POST方法。
        当请求失败时，会自动重试，直到达到最大重试次数。
        
        Args:
            method (str): HTTP方法，"get"或"post"
            url (str): 请求URL
            headers (dict): 请求头
            data (dict, optional): 请求数据，默认为None
            
        Returns:
            requests.Response: 请求响应对象
            
        Raises:
            requests.RequestException: 当请求失败且重试次数用尽时抛出
            ValueError: 当响应内容无法解析时抛出
        """
        method = method.lower()
        if method not in ["get", "post"]:
            raise ValueError(f"不支持的HTTP方法: {method}")
            
        for i in range(self.MAX_RETRIES):
            try:
                if method == "post":
                    response = requests.post(url=url, headers=headers, data=data, timeout=self.TIMEOUT, verify=False)
                else:
                    response = requests.get(url=url, headers=headers, timeout=self.TIMEOUT, verify=False)
                
                response.raise_for_status()
                return response
            except requests.HTTPError as e:
                status_code = e.response.status_code if hasattr(e, 'response') else 'unknown'
                logger.warning(f"HTTP错误 (尝试 {i+1}/{self.MAX_RETRIES}): {url} - 状态码: {status_code}")
            except requests.ConnectionError:
                logger.warning(f"连接错误 (尝试 {i+1}/{self.MAX_RETRIES}): {url}")
            except requests.Timeout:
                logger.warning(f"请求超时 (尝试 {i+1}/{self.MAX_RETRIES}): {url}")
            except (requests.RequestException, ValueError) as e:
                logger.warning(f"请求失败 (尝试 {i+1}/{self.MAX_RETRIES}): {url} - {str(e)}")
            
            if i == self.MAX_RETRIES - 1:
                logger.error(f"请求失败，已达到最大重试次数: {url}")
                raise
            
            # 指数退避策略，每次重试等待时间增加
            wait_time = self.RETRY_DELAY * (2 ** i)
            logger.debug(f"等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

    def _generate_signed_post_data(self, data: dict) -> dict:
        """生成带签名的提交数据
        
        该方法用于生成带有签名的POST数据，用于各种API请求。
        签名算法基于MD5哈希，使用时间戳、随机字符串和密钥组合生成。
        
        Args:
            data (dict): 原始数据字典，包含请求所需的参数
            
        Returns:
            dict: 添加签名(sign)、时间戳(time)和随机字符串(sign_key)后的数据字典
        
        Note:
            此方法被多个API请求方法调用，如签到、任务完成、抽奖等
        """
        # 构建签名字符串
        sign_str = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
        sign_str += f"&key={self.key}"
        
        # 计算签名
        sign = hashlib.md5(bytes(sign_str, encoding="utf-8")).hexdigest().upper()
        data["sign"] = sign
        
        return data

    def _robot_token(self, headers):
        '''获取token'''
        url = 'https://user-api.smzdm.com/robot/token'
        ts = int(round(time.time() * 1000))
        data = {
            "basic_v": 0,
            "f": self.device,
            "v": self.app_ver,
            "time": ts,
            "weixin": self.is_wx,
            "zhuanzai_ab": "b"
        }

        data = self._generate_signed_post_data(data)
        response = self._request_with_retry("post", url, headers, data)
        result = response.json()
        return result["data"]["token"]

    def _sign(self, headers, token):
        '''签到'''
        timestamp = int(round(time.time() * 1000))
        data = {
            "f": self.device,
            "v": self.app_ver,
            "sk": self.sk,
            "weixin": self.is_wx,
            "time": timestamp,
            "token": token
        }
        
        data = self._generate_signed_post_data(data)
        url = "https://user-api.smzdm.com/checkin"
        response = self._request_with_retry("post", url, headers, data)
        ret = response.json()
        msg = [
            {"name": "签到结果", "value": ret["error_msg"]},
            {"name": "补签卡", "value": ret['data']['cards']},
            {"name": "金币", "value": ret['data']['cgold']},
            {"name": "碎银", "value": ret['data']['pre_re_silver']},
        ]
        return msg, data

    def _all_reward(self, headers, data):
        '''获取奖励结果'''
        url2 = "https://user-api.smzdm.com/checkin/all_reward"
        response = self._request_with_retry("post", url2, headers, data)
        result = response.json()
        msgs = []
        if result['error_code'] == '0':
            normal_reward = result["data"]["normal_reward"]
        
            msgs = [
                {
                    "name": "今日签到奖励",
                    "value": normal_reward["gift"]["content_str"],
                },
                {
                    "name": "签到奖励",
                    "value": normal_reward["reward_add"]["content"],
                },
                {
                    "name": "连续签到",
                    "value": normal_reward["sub_title"],
                },
            ]
        return msgs

    def sign_main(self):
        '''签到和连续签到奖励'''
        token = self._robot_token(self.headers)
        msg, data = self._sign(self.headers, token)
        extra_reward = self._get_extra_reward()
        msg.append({"name": "额外奖励", "value": extra_reward})
        reward_msg = self._all_reward(self.headers, data)
        msg += reward_msg
        msg = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg])
        logger.info(msg)

    def _event_view_article_sync(self, task, headers):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/task/event_view_article_sync'
        data = {
            "article_id": task["article_id"],
            "f": self.device,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "time": ts,
            "task_id": task["task_id"],
            "channel_id": task["channel_id"]
        }
        
        data = self._generate_signed_post_data(data)

        response = self._request_with_retry("post", url, headers, data).json()
        logger.debug(response)
        
    def _activity_task_receive(self, task_id, robot_token, headers):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/task/activity_task_receive'
        data = {
            "f": self.device,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "time": ts,
            "task_id": task_id,
            "robot_token": robot_token
        }
        
        data = self._generate_signed_post_data(data)

        response = self._request_with_retry("post", url, headers, data).json()
        logger.debug(response)
        if int(response['error_code']) == 0:
            logger.info(clean_html(response['data']['reward_msg']))
    
    def _get_activity_task_list(self, activity_id):
        '''获取指定活动的任务列表
        
        通过API获取指定活动的任务列表，包括任务ID、名称、状态等信息
        
        Args:
            activity_id (str): 活动ID
            
        Returns:
            tuple: (活动名称, 开始时间, 结束时间, 任务列表), 如果请求失败则返回(None, None, None, [])
        '''
        url = f'https://zhiyou.m.smzdm.com/task/task/ajax_get_activity_info?activity_id={activity_id}'
        response = self._request_with_retry("get", url, self.zhiyou_headers).json()
        
        if response["error_code"] == 0:
            ret_data = response.get('data', '')
            if ret_data:
                activity_name = ret_data.get('activity_name', '')
                start_date = datetime.fromtimestamp(ret_data.get('activity_start_time', 0))
                end_date = datetime.fromtimestamp(ret_data.get('activity_end_time', 0))
                task_list = ret_data["activity_task"]["default_list"]
                return activity_name, start_date, end_date, task_list
        else:
            logger.error(f"获取活动任务列表失败({activity_id}):{response['error_msg']}")
        
        return None, None, None, []
    
    def do_activity_task(self, activity_id_list = None):
        '''完成活动任务

        Args:
            activity_id_list (list): 活动ID列表

        Returns:
            None
            
        Note:
            1. 通过活动ID获取活动任务列表
            2. 遍历任务列表，对每个任务调用_process_task方法进行处理
            3. 任务处理包括浏览文章、同步开始信息、领取奖励等步骤
        '''
        if activity_id_list is None:
            activity_id_list = self.activity_list
            
        for activity_id in activity_id_list:
            activity_name, start_date, end_date, task_list = self._get_activity_task_list(activity_id)
            
            if not activity_name:
                continue
                
            if end_date >= datetime.now():
                logger.info(f'开始 活动任务{activity_name}({activity_id})。')
                for task in task_list:
                    self._process_task(task)
            else:
                logger.info(f'活动任务{activity_name}({activity_id})已结束。')
        
    def _process_task(self, task: json):
        """处理并完成单个任务
        
        根据任务类型执行不同的操作，如浏览文章、同步任务状态、领取奖励等
        
        Args:
            task (json): 任务信息，包含任务ID、名称、类型、状态等
            
        Returns:
            None
        """
        if task["task_event_type"] == "interactive.view.article" and int(task["task_status"]) != 4:
            # 浏览文章任务
            logger.info(f'Do {task["task_name"]} {task["task_button_text"] if "task_button_text" in task else ""}({task["task_id"]}):')
            
            pretty = json.dumps(task, ensure_ascii=False, indent=2)
            logger.debug(pretty)

            # 根据task_even_num循环执行任务
            for _ in range(int(task['task_even_num']) - int(task['task_finished_num'])):
                # 获取token
                token = self._robot_token(self.headers)
                time.sleep(1)
                # 同步开始信息
                self._event_view_article_sync(task, self.headers)
                time.sleep(11)
                # 完成任务
                self._activity_task_receive(task["task_id"], token, self.headers)
                time.sleep(2)
        else:
            logger.info(
                f'Task {task["task_name"]}({task["task_id"]}) 任务 '
                f'{"已完成" if task["task_status"] == 4 else "类型" + task["task_event_type"] + "我做不来"}。'
            )
        
    def _show_view(self):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/checkin/show_view_v2'
        data = {
            "zhuanzai_ab": "b",
            "weixin": self.is_wx,
            "f": self.device,
            "v": self.app_ver,
            "time": ts, 
            "basic_v": 0
        }
        
        data = self._generate_signed_post_data(data)
        
        response = self._request_with_retry("post", url, self.headers, data)
        if response.status_code == 200:
            return response.json()
        
        raise Exception(f'返回错误：{response.text}')
    
    def _extra_reward(self):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/checkin/extra_reward'
        data = {
            "basic_v": 0,
            "f": self.device,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "time": ts,
            "zhuanzai_ab": "b"
        }
        
        data = self._generate_signed_post_data(data)
        response = self._request_with_retry("post", url, self.headers, data)
        
        if response.status_code == 200:
            return response.json()
        
        raise Exception(f'返回错误：{response.text}')

    def _get_extra_reward(self):
        '''
        获取额外奖励，返回获奖结果
        
        返回json结果示例：
        {
            "error_code": "0",
            "error_msg": "",
            "smzdm_id": "6764418738",
            "s": "67ef4d591a2e0296411",
            "data": {
                "title": "额外奖励",
                "gift": {
                    "gift_id": "4108",
                    "pic": "https://res.smzdm.com/app/images/user/popup/img_integral.png",
                    "content": "<span style=\"font-size: 15px;color: #333333;\">经验<strong><span style=\"color: #f04848;\">+10</span></strong></span>"
                },
                "pop": [],
                "adx_ad": {
                    "adx_pop_sign": "5000101"
                }
            }
        }
        '''
        ret = self._show_view() # 获取签到页面json，判断是否需要获取额外奖励

        if int(ret['error_code']) == 0:
            if (bool(ret['data']['rows'][0]['cell_data']['checkin_continue']['continue_checkin_reward_show'])):
                # 如果需要获取连续签到的额外奖励
                ret_reward = self._extra_reward()
                if int(ret_reward['error_code']) == 0:
                    pattern = r'>([^<]+)<'  # 匹配>和<之间的非<字符
                    result = ''.join(re.findall(pattern, ret_reward['data']['gift']['content']))
                    return result  # 输出: 经验+10                
                else:
                    return ret_reward['error_msg']
            if (int(ret['data']['rows'][1]['cell_data']['activity_reward_status']) != 0):
                # 如果有任务完成奖励自动获取
                return self._get_activity_receive(ret['data']['rows'][1]['cell_data']['activity_id'])
        else:
            return ret['error_msg']

    def _get_activity_receive(self, activity_id):
        '''获取任务阶段奖励'''
        url = 'https://user-api.smzdm.com/task/activity_receive'
        ts = int(round(time.time() * 1000))
        data = {
            "basic_v": 0,
            "f": self.device,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "activity_id": activity_id,
            "time": ts,
            "zhuanzai_ab": "b",
        }

        data = self._generate_signed_post_data(data)
        
        response = self._request_with_retry("post", url, self.headers, data).json()
        logger.debug(response)
        if int(response['error_code']) == 0:
            return clean_html(response['data']['reward_msg'])
        return response['error_msg']

    def _get_rank_list(self):
        '''获取排行榜文章列表'''
        headers = {
            "accept-encoding": "gzip",
            "Cookie": self.cookie,
            "User-Agent": "smzdm_android_V10.4.1 rv:841 (22021211RC;Android12;zh)smzdmapp",
        }
        ts = int(round(time.time() * 1000))
        url = 'https://haojia-api.smzdm.com/ranking_list/articles'
        params = {
            "basic_v": 0,
            "channel_id": 0,
            "exclude_article_ids": "null",
            "f": "android",
            "limit": 20,
            "offset": 0,
            "sub_tab": 0,
            "tab": 1,
            "time": ts,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "zhuanzai_ab": "b"
        }
        
        params = self._generate_signed_post_data(params)
        
        # 构建完整的URL参数字符串
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        response = self._request_with_retry("get", f"{url}?{query_string}", headers)
        
        if response.status_code == 200:
            ret = response.json()
            if int(ret['error_code']) == 0:
                for article in ret['data']['rows']:
                    if article['cell_type'] != '21017':
                        logger.info(f'{article["article_title"]} {article["article_price"]}:值{article.get("article_worthy", 0)}/不值{article.get("article_unworthy",0)} 评论{article.get("article_comment",0)}')
        # logger.debug(response.text)

    def _get_task_list(self):
        """获取签到页面的任务
        
        通过API获取签到页面的任务列表，包括任务ID、名称、状态等信息
        
        Returns:
            list: 包含任务详细信息的列表，如果请求失败则返回空列表
            
        Note:
            该方法使用_generate_signed_post_data生成签名数据
        """
        url = 'https://user-api.smzdm.com/task/list_v2'
        ts = int(round(time.time() * 1000))
        data = {
            "basic_v": 0,
            "f": self.device,
            "time": ts,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "zhuanzai_ab": "b"
        }

        data = self._generate_signed_post_data(data)

        response = self._request_with_retry("post", url, self.headers, data)
        
        task_list = []
        
        if response.status_code == 200:
            ret = response.json()
            if int(ret['error_code']) == 0:
                for task_main in ret['data']['rows'][0]['cell_data']['activity_task']['accumulate_list']['task_list_v2']:
                    for task in task_main['task_list']:
                        task_list.append(task)

        return task_list

    def do_sign_page_task(self):
        """完成签到页任务"""
        
        logger.info('开始 签到页任务。')
        
        # 获取任务列表
        task_list = self._get_task_list()
        
        # 完成任务列表里可以完成的阅览任务
        for task in task_list:
            self._process_task(task)
            
        # 完成任务后确认是否有阶段奖励，并领取。
        self._get_extra_reward()

    def _query_lottery_times(self, active_id: str) -> int:
        '''
        查询指定活动的剩余抽奖次数
        
        通过API获取指定抽奖活动的剩余免费抽奖次数
        
        Args:
            active_id (str): 活动ID
            
        Returns:
            int: 剩余免费抽奖次数，如果查询失败返回0
            
        Note:
            该方法会解析API返回的JSON数据，提取remain_free_lottery_count字段
        '''
        ts = int(round(time.time() * 1000))
        url = f'https://zhiyou.smzdm.com/user/lottery/jsonp_get_current?active_id={active_id}&_={ts}&callback=jQuery{ts}_{ts}'
        response = self._request_with_retry("get", url, self.zhiyou_headers)
        if response.status_code == 200:
            # s = 'jQuery1745651794961_1745651794961({"smzdm_id":"6764418738","remain_free_lottery_count":2,"remain_charging_lottery_count":0,"charging_lottery_cost":0,"charging_lottery_cost_method":"silver","can_draw":true,"sys_date":"2025-04-26 15:16:34"})'
            match = re.search(r'\((\{.*\})\)', response.text)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                times = int(data.get('remain_free_lottery_count'))
                return times
        return 0

    def _lottery(self, active_id: str) -> int:
        '''
        执行抽奖操作
        
        通过API执行指定活动的抽奖操作，并返回剩余抽奖次数
        
        Args:
            active_id (str): 抽奖活动ID
            
        Returns:
            int: 剩余抽奖次数，如果抽奖成功返回剩余次数，如果失败返回0
            
        Note:
            该方法会解析API返回的JSON数据，提取remain_free_lottery_count字段
            同时会记录抽奖结果信息到日志
        '''
        url = f"https://zhiyou.smzdm.com/user/lottery/jsonp_draw?active_id={active_id}"
        response = self._request_with_retry("post", url, self.zhiyou_headers).json()
        if response['error_code'] == 0:
            logger.info(response['error_msg'])
            return int(response['data']['remain_free_lottery_count'])
        else:
            logger.error(response['error_msg'])
        return 0
    
    def _get_lottery_info(self, active_id):
        '''获取抽奖活动详细信息
        
        通过API获取指定抽奖活动的详细信息，包括活动名称、开始时间、结束时间等
        
        Args:
            active_id (str): 抽奖活动ID
            
        Returns:
            dict: 包含活动详细信息的字典，如活动名称、开始时间、结束时间等
        '''
        url = f"https://zhiyou.smzdm.com/user/lottery/jsonp_get_active_info?active_id={active_id}"
        response = self._request_with_retry("get", url, self.zhiyou_headers).json()
        return response.get('data', {})

    def do_lottery(self, active_id_list = None):
        '''完成抽奖任务

        Args:
            active_id_list (list): 活动ID列表

        Returns:
            None
            
        Note:
            1. 遍历活动列表中的每个活动ID
            2. 查询每个活动的剩余抽奖次数
            3. 如果有剩余抽奖次数，则进行抽奖
            4. 抽奖后等待1秒，避免请求过于频繁
        '''
        if active_id_list is None:
            active_id_list = self.lottery_list
        for active_id in active_id_list:
            ret_data = self._get_lottery_info(active_id)
            logger.info(f'开始 抽奖{ret_data["active_name"]}({active_id})。')
            if ret_data:
                start_date = ret_data.get('start_date', '')
                end_date = ret_data.get('end_date', '')
                lottery_times = self._query_lottery_times(active_id)
                if (datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") >= datetime.now()) and (lottery_times > 0):
                    while self._lottery(active_id) > 0:
                        time.sleep(2)  # 避免请求过于频繁
                else:
                    if datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") < datetime.now():
                        logger.info(f'抽奖任务{ret_data["active_name"]}({active_id})已结束。')
                    else:
                        logger.info(f'抽奖任务{ret_data["active_name"]}({active_id})抽奖次数已用完。')

    def _access_active_page(self, page_id):
        '''访问活动页面并收集活动ID和抽奖ID
        
        Args:
            page_id (str): 活动页面ID
            
        Returns:
            tuple: (活动标题, 活动ID列表, 抽奖ID列表)
        '''
        if '/' in page_id:
            url = f'https://m.smzdm.com/topic/{page_id}'
        else:
            url = f'https://post.m.smzdm.com/ajax_m/activity/{page_id}'
        response = self._request_with_retry("get", url, self.zhiyou_headers)
        if response.status_code == 200:
            if '/' in page_id:
                page_content_match = re.search(r'<script id="page-content">window\.pageContent=(.*?)</script>', response.text)
                if page_content_match:
                    
                    json_text = page_content_match.group(1)
                    data = json.loads(json_text)

                    title = data['name']
                    logger.info(f"访问任务 {title}({page_id})")
                    data = json.loads(data.get('content', ''))
                    child_list = data.get('child', '')

                    pretty = json.dumps(data, ensure_ascii=False, indent=2)
                    logger.debug(pretty)

                    id_list = []
                    lottery_list = []
                    self._collect_ids(child_list, id_list, lottery_list)
                    return title, id_list, lottery_list
            else:
                json_text = extract_and_decode_base64(response.text)
                data = json.loads(json_text)

                pretty = json.dumps(data, ensure_ascii=False, indent=2)
                logger.debug(pretty)

                if len(data) > 0:
                    info = data.get('info', '')
                    if info:
                        title = info.get('title', '')
                        start_date = info.get('start_time', '')
                        end_date = info.get('end_time', '')
                        logger.info(f"访问任务 {title}({page_id})")
                            
                        if datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") >= datetime.now():
                        
                            data = data.get('game_list', '')
                            # pretty = json.dumps(data, ensure_ascii=False, indent=2)
                            # logger.debug(pretty)
                            id_list = []
                            lottery_list = []
                            for temp in data:
                                temp_id = temp.get('id', '')
                                temp_lottery_id = temp.get('lottery_id', '')
                                if temp_id:
                                    id_list.append(temp_id)
                                if temp_lottery_id:
                                    lottery_list.append(temp_lottery_id)
                            return title, id_list, lottery_list
                        else:
                            logger.error(f"任务{title}({page_id})已结束，时间范围：{start_date}~{end_date}")
        return None, None, None
    
    def do_active(self, topic_page_list = None):
        '''完成活动任务'''
        if topic_page_list is None:
            topic_page_list = self.topic_page_list
        for active_id in topic_page_list:
            tilte, id_list, lottery_list = self._access_active_page(active_id)
            # 对id_list和lottery_list进行去重
            id_list = list(set(id_list))
            lottery_list = list(set(lottery_list))
            
            logger.debug(f"{tilte} id: {str(id_list)}  lottery_id: {str(lottery_list)}")
            if not (tilte is None):
                self.do_activity_task(id_list)
                time.sleep(2)
                self.do_lottery(lottery_list)
            time.sleep(2)

    def _collect_ids(self, child_list, id_list, lottery_list):
        '''递归收集活动的任务ID和抽奖ID
        
        从活动页面的JSON数据中提取任务ID和抽奖ID，支持递归处理嵌套结构
        
        Args:
            child_list (list): 包含子元素的列表
            id_list (list): 用于存储收集到的任务ID
            lottery_list (list): 用于存储收集到的抽奖ID
            
        Returns:
            None: 结果直接修改传入的id_list和lottery_list
        '''
        for child in child_list:
            if child.get('type', '') == 'prod/compTwentap' or child.get('type', '') == 'prod/compLottery':
                lottery_list.append(child['props']['hashId'])
                logger.debug(f"{child['props']['hashId']}:{child['props']['rulesText']}")
            if child.get('type', '') == 'prod/compTask':
                id_list.append(child['props']['taskId'])
                logger.debug(f"{child['props']['taskId']}:{child['label']}")
            # 递归处理子节点
            if 'child' in child and isinstance(child['child'], list) and child['child']:
                self._collect_ids(child['child'], id_list, lottery_list)

if __name__ == "__main__":

    accounts = get_user_infos(APP)
    app_configs = get_app_configs(APP)
    if not accounts:
        logger.error("未找到有效的账户配置信息")
        exit(1)

    for account in accounts:
        cookie_str = account['cookie']
        logger.info(f"开始执行 {account['name']} 账号的任务")
    
        smzdm = SMZDM(cookie_str)
        smzdm.sign_main()
        smzdm.do_sign_page_task()
        smzdm.do_active(app_configs.get('topic_page_list', []))
        smzdm.do_activity_task(app_configs.get('activity_list', []))
        smzdm.do_lottery(app_configs.get('lottery_list', []))
        logger.info(f"执行 {account['name']} 账号的任务完成")
        time.sleep(2)
