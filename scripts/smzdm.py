import hashlib
import json
import os
import re
import time
import requests
import urllib3
# from dailycheckin import CheckIn
from loguru import logger
from datetime import datetime

import base64

urllib3.disable_warnings()

APP = 'smzdm'

# 获取账户信息
def get_account_info():

    try:
        # 如果本地文件读取失败，尝试从环境变量获取
        accounts = json.loads(os.environ.get(APP))
    except Exception:
        accounts = None

    if accounts == None:
        print('No Account info')
        exit(0)
    
    return accounts


def clean_html(html_string):
    """去除字符串中HTML标签"""
    pattern = re.compile(r'<[^>]+>')
    return pattern.sub('', html_string).strip()

def extract_and_decode_base64(input_str):
    # 利用正则表达式找出单引号间的 Base64 编码字符串
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
    
    active_list = ['daY8jNa8Oo', 'PmR8xlA8wy']
    
    activity_list = ['789', '804', '807', '810', '813', '814', '817', '818', '820']
    
    name = "什么值得买"
    app_ver = '10.4.1'
    is_wx = '1'
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

    def __init__(self, check_item: dict):
        self.check_item = check_item
        self.cookie = self.check_item.get("cookie")
        self.headers['Cookie'] = self.cookie
        self.zhiyou_headers['Cookie'] = self.cookie

    def request_with_retry(self, method, url, headers, data=None, max_retries=3):
        for i in range(max_retries):
            try:
                if method == "post":
                    response = requests.post(url=url, headers=headers, data=data, timeout=10, verify=False)
                else:
                    response = requests.get(url=url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
                return response
            except (requests.RequestException, ValueError) as e:
                if i == max_retries - 1:
                    raise
                time.sleep(2)

    def robot_token(self, headers):
        ts = int(round(time.time() * 1000))
        url = "https://user-api.smzdm.com/robot/token"
        data = {
            "f": "android",
            "v": self.app_ver,
            "weixin": self.is_wx,
            "time": ts,
            "sign": hashlib.md5(
                bytes(
                    f"f=android&time={ts}&v={self.app_ver}&weixin={self.is_wx}&key={self.key}",
                    encoding="utf-8",
                )
            ).hexdigest().upper(),
        }
        response = self.request_with_retry("post", url, headers, data)
        result = response.json()
        return result["data"]["token"]

    def sign(self, headers, token):
        timestamp = int(round(time.time() * 1000))
        data = {
            "f": "android",
            "v": self.app_ver,
            "sk": self.sk,
            "weixin": self.is_wx,
            "time": timestamp,
            "token": token,
            "sign": hashlib.md5(
                bytes(
                    f"f=android&sk={self.sk}&time={timestamp}&token={token}&v={self.app_ver}&weixin={self.is_wx}&key={self.key}",
                    encoding="utf-8",
                )
            ).hexdigest().upper(),
        }
        url = "https://user-api.smzdm.com/checkin"
        response = self.request_with_retry("post", url, headers, data)
        ret = response.json()
        # logger.debug(response.json())
        msg = [
            {"name": "签到结果", "value": ret["error_msg"]},
            {"name": "补签卡", "value": ret['data']['cards']},
            {"name": "金币", "value": ret['data']['cgold']},
            {"name": "碎银", "value": ret['data']['pre_re_silver']},
        ]
        return msg, data

    def all_reward(self, headers, data):
        url2 = "https://user-api.smzdm.com/checkin/all_reward"
        response = self.request_with_retry("post", url2, headers, data)
        result = response.json()
        # logger.debug(result)
        msgs = []
        if result['error_code'] == '0':
            normal_reward = result["data"]["normal_reward"]
        # if normal_reward := result["data"]["normal_reward"]:
        
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

    def main(self):
        token = self.robot_token(self.headers)
        msg, data = self.sign(self.headers, token)
        extra_reward = self.get_extra_reward()
        msg.append({"name": "额外奖励", "value": extra_reward})
        reward_msg = self.all_reward(self.headers, data)
        msg += reward_msg
        msg = "\n".join([f"{one.get('name')}: {one.get('value')}" for one in msg])
        return msg

    def _event_view_article_sync(self, task, headers):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/task/event_view_article_sync'
        data = {
            "article_id": task["article_id"],
            "f": "android",
            "v": "10.4.1",
            "weixin": 1,
            "time": ts,
            "task_id": task["task_id"],
            "channel_id": task["channel_id"],
            "sign": hashlib.md5(
                bytes(
                    f'article_id={task["article_id"]}&channel_id={task["channel_id"]}&f=android&task_id={task["task_id"]}&time={ts}&v=10.4.1&weixin=1&key=apr1$AwP!wRRT$gJ/q.X24poeBInlUJC',
                    encoding="utf-8",
                )
            ).hexdigest().upper(),
        }

        response = self.request_with_retry("post", url, headers, data).json()
        logger.debug(response)
        
    def _activity_task_receive(self, task_id, robot_token, headers):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/task/activity_task_receive'
        data = {
            "f": "android",
            "v": "10.4.1",
            "weixin": 1,
            "time": ts,
            "task_id": task_id,
            "robot_token": robot_token,
            "sign": hashlib.md5(
                bytes(
                    f'f=android&robot_token={robot_token}&task_id={task_id}&time={ts}&v=10.4.1&weixin=1&key=apr1$AwP!wRRT$gJ/q.X24poeBInlUJC',
                    encoding="utf-8",
                )
            ).hexdigest().upper(),
        }

        response = self.request_with_retry("post", url, headers, data).json()
        logger.debug(response)
        if int(response['error_code']) == 0:
            logger.info(clean_html(response['data']['reward_msg']))
    
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
        
            url = f'https://zhiyou.m.smzdm.com/task/task/ajax_get_activity_info?activity_id={activity_id}'
            response = self.request_with_retry("get", url, self.zhiyou_headers).json()

            if (response["error_code"] == 0):
                if response["data"]:
                    logger.info(f'开始 活动任务{response["data"]["activity_name"]}({activity_id})。')
                    for task in response["data"]["activity_task"]["default_list"]:
                        # logger.debug(task["task_name"])
                        self._process_task(task)
            else:
                logger.error(response['error_msg'])
        
    def _process_task(self, task: json):
        """完成浏览任务"""
        if task["task_event_type"] == "interactive.view.article" and int(task["task_status"]) != 4:
            logger.info(f'Do task {task["task_name"]} {task["task_button_text"] if "task_button_text" in task else ""}:')
            # 根据task_even_num循环执行任务
            for _ in range(int(task['task_even_num']) - int(task['task_finished_num'])):
                # 获取token
                token = self.robot_token(self.headers)
                time.sleep(1)
                # 同步开始信息
                self._event_view_article_sync(task, self.headers)
                time.sleep(11)
                # 完成任务
                self._activity_task_receive(task["task_id"], token, self.headers)
                time.sleep(2)
        else:
            logger.info(
                f'Task {task["task_id"]} {task["task_name"]} 任务 '
                f'{"已完成" if task["task_status"] == 4 else "类型" + task["task_event_type"] + "我做不来"}。'
            )
        
    def _show_view(self):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/checkin/show_view_v2'
        data = {
            "zhuanzai_ab": "b",
            "weixin": 1,
            "f": "android",
            "v": "10.4.1",
            "sign": hashlib.md5(
                bytes(f'basic_v=0&f=android&time={ts}&v=10.4.1&weixin=1&zhuanzai_ab=b&key={self.key}', encoding="utf-8",)
            ).hexdigest().upper(),
            "time": ts, 
            "basic_v": 0
        }
        
        response = self.request_with_retry("post", url, self.headers, data)
        if response.status_code == 200:
            return response.json()
        
        raise Exception(f'返回错误：{response.text}')
    
    def _extra_reward(self):
        ts = int(round(time.time() * 1000))
        url = 'https://user-api.smzdm.com/checkin/extra_reward'
        data = {
            "basic_v": 0,
            "f": "android",
            "v": "10.4.1",
            "weixin": 1,
            "time": ts,
            "zhuanzai_ab": "b",
            "sign": hashlib.md5(
                bytes(
                    f'basic_v=0&f=android&time={ts}&v=10.4.1&weixin=1&zhuanzai_ab=b&key=apr1$AwP!wRRT$gJ/q.X24poeBInlUJC',
                    encoding="utf-8",
                )
            ).hexdigest().upper(),
        }
        response = self.request_with_retry("post", url, self.headers, data)
        
        if response.status_code == 200:
            return response.json()
        
        raise Exception(f'返回错误：{response.text}')

    def get_extra_reward(self):
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
            "f": "android",
            "v": "10.4.1",
            "weixin": 1,
            "activity_id": activity_id,
            "time": ts,
            "zhuanzai_ab": "b",
        }

        data = self._generate_signed_post_data(data)
        
        response = self.request_with_retry("post", url, self.headers, data).json()
        logger.debug(response)
        if int(response['error_code']) == 0:
            return clean_html(response['data']['reward_msg'])
        return response['error_msg']

    def _generate_signed_post_data(self, data: dict) -> dict:
        '''生成带签名的提交数据'''

        # 构建签名字符串
        sign_str = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
        sign_str += f"&key={self.key}"
        
        # 计算签名
        sign = hashlib.md5(bytes(sign_str, encoding="utf-8")).hexdigest().upper()
        data["sign"] = sign
        
        return data

    def _get_rank_list(self):
        headers = {
            "accept-encoding": "gzip",
            "Cookie": self.check_item.get("cookie"),
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
        
        # 构建签名字符串
        sign_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        sign_str += f"&key={self.key}"
        
        # 计算签名
        sign = hashlib.md5(bytes(sign_str, encoding="utf-8")).hexdigest().upper()
        params["sign"] = sign
        
        # 构建完整的URL参数字符串
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])

        response = self.request_with_retry("get", f"{url}?{query_string}", headers)
        
        if response.status_code == 200:
            ret = response.json()
            if int(ret['error_code']) == 0:
                for article in ret['data']['rows']:
                    if article['cell_type'] != '21017':
                        logger.info(f'{article["article_title"]} {article["article_price"]}:值{article.get("article_worthy", 0)}/不值{article.get("article_unworthy",0)} 评论{article.get("article_comment",0)}')
        # logger.debug(response.text)

    def _get_task_list(self):
        """获取签到页面的任务"""
        url = 'https://user-api.smzdm.com/task/list_v2'
        ts = int(round(time.time() * 1000))
        data = {
            "basic_v": 0,
            "f": "android",
            "time": ts,
            "v": self.app_ver,
            "weixin": self.is_wx,
            "zhuanzai_ab": "b"
        }

        data = self._generate_signed_post_data(data)

        response = self.request_with_retry("post", url, self.headers, data)
        
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
        self.get_extra_reward()

    def _query_lottery_times(self, active_id: str) -> int:
        '''
        查询指定活动的剩余抽奖次数
        
        Args:
            active_id (str): 活动ID
            
        Returns:
            int: 剩余免费抽奖次数，如果查询失败返回0
        '''
        ts = int(round(time.time() * 1000))
        url = f'https://zhiyou.smzdm.com/user/lottery/jsonp_get_current?active_id={active_id}&_={ts}&callback=jQuery{ts}_{ts}'
        response = self.request_with_retry("get", url, self.zhiyou_headers)
        if response.status_code == 200:
            # s = 'jQuery1745651794961_1745651794961({"smzdm_id":"6764418738","remain_free_lottery_count":2,"remain_charging_lottery_count":0,"charging_lottery_cost":0,"charging_lottery_cost_method":"silver","can_draw":true,"sys_date":"2025-04-26 15:16:34"})'
            match = re.search(r'\((\{.*\})\)', response.text)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                times = int(data.get('remain_free_lottery_count'))
                if times == 0 : logger.info('无抽奖机会。')
                return times
        return 0

    def _lottery(self, active_id: str) -> int:
        '''
        抽奖函数
        
        Args:
            active_id: 活动ID
            
        Returns:
            int: 剩余抽奖次数
        '''
        url = f"https://zhiyou.smzdm.com/user/lottery/jsonp_draw?active_id={active_id}"
        response = self.request_with_retry("post", url, self.zhiyou_headers).json()
        if response['error_code'] == 0:
            logger.info(response['error_msg'])
            return int(response['data']['remain_free_lottery_count'])
        else:
            logger.error(response['error_msg'])
        return 0
    
    def _get_lottery_reward(self, active_id):
        '''获取活动的奖品内容（用处不大）'''
        url = f"https://zhiyou.smzdm.com/user/lottery/jsonp_get_active_info?active_id={active_id}"
        response = self.request_with_retry("get", url, self.zhiyou_headers).json()
        logger.debug(f"{response['data']['start_date']}~{response['data']['end_date']} {response['data']['active_name']}")

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
            active_id_list = self.active_list
        for active_id in active_id_list:
            logger.info(f'开始 抽奖任务{active_id}。')
            self._get_lottery_reward(active_id)
            if self._query_lottery_times(active_id) > 0:
                while self._lottery(active_id) > 0:
                    time.sleep(1)  # 避免请求过于频繁

    def _access_active_page(self, page_id):
        if '/' in page_id:
            url = f'https://m.smzdm.com/topic/{page_id}'
        else:
            url = f'https://post.m.smzdm.com/ajax_m/activity/{page_id}'
        response = self.request_with_retry("get", url, self.zhiyou_headers)
        if response.status_code == 200:
            if '/' in page_id:
                page_content_match = re.search(r'<script id="page-content">window\.pageContent=(.*?)</script>', response.text)
                if page_content_match:
                    
                    json_text = page_content_match.group(1)
                    # logger.debug(json_text)
                    data = json.loads(json_text)
                    title = data['name']
                    logger.info(f"访问任务 {title}")
                    data = json.loads(data.get('content', ''))
                    child_list = data.get('child', '')
                    # pretty = json.dumps(child_list, ensure_ascii=False, indent=2)
                    # logger.debug(pretty)
                    id_list = []
                    lottery_list = []
                    collect_ids(child_list, id_list, lottery_list)
                    return title, id_list, lottery_list
            else:
                json_text = extract_and_decode_base64(response.text)
                data = json.loads(json_text)

                # pretty = json.dumps(data, ensure_ascii=False, indent=2)
                # logger.debug(pretty)
                if len(data) > 0:
                    info = data.get('info', '')
                    if info:
                        title = info.get('title', '')
                        start_date = info.get('start_time', '')
                        end_date = info.get('end_time', '')
                        logger.info(f"访问任务 {title}")
                            
                        if datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S") > datetime.now():
                        
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
                            logger.error(f"任务已超时，时间范围：{start_date}~{end_date}")
        return None, None, None
    
    def do_active(self, active_list_id):
        for active_id in active_list_id:
            tilte, id_list, lottery_list = self._access_active_page(active_id)
            logger.debug(f"{tilte} id: {str(id_list)}  lottery_id: {str(lottery_list)}")
            if not (tilte is None):
                self.do_activity_task(id_list)
                time.sleep(1)
                self.do_lottery(lottery_list)
            time.sleep(1)

def collect_ids(child_list, id_list, lottery_list):
    for child in child_list:
        if child.get('type', '') == 'prod/compTwentap' or child.get('type', '') == 'prod/compLottery':
            lottery_list.append(child['props']['hashId'])
            logger.debug(f"{child['props']['hashId']}:{child['props']['rulesText']}")
        if child.get('type', '') == 'prod/compTask':
            id_list.append(child['props']['taskId'])
            logger.debug(f"{child['props']['taskId']}:{child['label']}")
        # 递归处理子节点
        if 'child' in child and isinstance(child['child'], list) and child['child']:
            collect_ids(child['child'], id_list, lottery_list)

if __name__ == "__main__":
    # with open(
    #     os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json"),
    #     encoding="utf-8",
    # ) as f:
    #     datas = json.loads(f.read())
    # _check_item = datas.get("SMZDM", [])[0]
    # print(SMZDM(check_item=_check_item).main())
    cookie = '{"cookies": [{"sameSite": "Lax", "name": "__ckguid", "value": "ws44nIliaKtNby2cjL7kFh", "domain": ".smzdm.com", "path": "/", "expires": 1766399944.475085, "httpOnly": true, "secure": false}, {"sameSite": "Lax", "name": "device_id", "value": "21307064331734863943344580118fe043e9c4c4bd0281d22f286a8cc4", "domain": ".smzdm.com", "path": "/", "expires": 2050223944.475227, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "homepage_sug", "value": "c", "domain": ".smzdm.com", "path": "/", "expires": 2050223975.650148, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "r_sort_type", "value": "score", "domain": ".smzdm.com", "path": "/", "expires": 2050223975.650187, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "_zdmA.vid", "value": "*", "domain": ".www.smzdm.com", "path": "/", "expires": 1734865775, "httpOnly": false, "secure": false}, {"sameSite": "None", "name": "HMACCOUNT_BFESS", "value": "0BAB534A465A6845", "domain": ".hm.baidu.com", "path": "/", "expires": 2147385600.952754, "httpOnly": false, "secure": true}, {"sameSite": "Lax", "name": "Hm_lvt_9b7ac3d38f30fe89ff0b8a0546904e58", "value": "1734863945", "domain": ".smzdm.com", "path": "/", "expires": 1766399975, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "HMACCOUNT", "value": "0BAB534A465A6845", "domain": ".smzdm.com", "path": "/", "expires": -1, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "sajssdk_2015_cross_new_user", "value": "1", "domain": ".smzdm.com", "path": "/", "expires": 1734883199, "httpOnly": false, "secure": false}, {"sameSite": "None", "name": "__jsluid_s", "value": "8ba8e28778e74a89ce608ac0b4b26d40", "domain": "shence-import.smzdm.com", "path": "/", "expires": 1766399946.042798, "httpOnly": true, "secure": true}, {"sameSite": "Lax", "name": "footer_floating_layer", "value": "0", "domain": ".www.smzdm.com", "path": "/", "expires": 1735468776, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "ad_date", "value": "22", "domain": ".www.smzdm.com", "path": "/", "expires": 1735468746, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "bannerCounter", "value": "%5B%7B%22number%22%3A0%2C%22surplus%22%3A1%7D%2C%7B%22number%22%3A0%2C%22surplus%22%3A1%7D%2C%7B%22number%22%3A0%2C%22surplus%22%3A1%7D%2C%7B%22number%22%3A0%2C%22surplus%22%3A1%7D%2C%7B%22number%22%3A0%2C%22surplus%22%3A1%7D%5D", "domain": ".www.smzdm.com", "path": "/", "expires": 1735468776, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "ad_json_feed", "value": "%7B%7D", "domain": ".www.smzdm.com", "path": "/", "expires": 1735468776, "httpOnly": false, "secure": false}, {"sameSite": "None", "name": "BAIDUID_BFESS", "value": "878CFA859C6161BD8E09037CA777FF5A:FG=1", "domain": ".baidu.com", "path": "/", "expires": 1766399946.322421, "httpOnly": false, "secure": true}, {"sameSite": "None", "name": "__jsluid_s", "value": "af02036145f9efd2c6b64bc0b641caf1", "domain": "logs-api.smzdm.com", "path": "/", "expires": 1766399947.174033, "httpOnly": true, "secure": true}, {"sameSite": "None", "name": "__jsluid_s", "value": "f7f93f926da1f2e8a1b65618539b97c1", "domain": "analytics-api.smzdm.com", "path": "/", "expires": 1766399954.258797, "httpOnly": true, "secure": true}, {"sameSite": "Lax", "name": "sess", "value": "BA-0ayJ1YqptdoBZAka6uRIA4qJZW1Qzwbh7eJaPCF63oJ6oQAZXMq1Bf%2BN12Hlxz4a3mOgIOCIw732J6uh%2FyAw08gKJ3MU9%2F8olyKBnVK%2BfqWnXGSx8zP90emM", "domain": ".smzdm.com", "path": "/", "expires": 1738751975.072443, "httpOnly": true, "secure": false}, {"sameSite": "Lax", "name": "user", "value": "user%3A6764418738%7C6764418738", "domain": ".smzdm.com", "path": "/", "expires": 1738751975.072459, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "smzdm_id", "value": "6764418738", "domain": ".smzdm.com", "path": "/", "expires": 2050223975.07247, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "_zdmA.uid", "value": "ZDMA.6DBBG55a4K.1734863976.2419200", "domain": ".smzdm.com", "path": "/", "expires": 1737283175, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "Hm_lpvt_9b7ac3d38f30fe89ff0b8a0546904e58", "value": "1734863976", "domain": ".smzdm.com", "path": "/", "expires": -1, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "sensorsdata2015jssdkcross", "value": "%7B%22distinct_id%22%3A%226764418738%22%2C%22first_id%22%3A%22193edf2ff2f2ae-0194f6f09e7233-6e577420-921600-193edf2ff30303%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%2C%22%24latest_landing_page%22%3A%22https%3A%2F%2Fwww.smzdm.com%2F%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTkzZWRmMmZmMmYyYWUtMDE5NGY2ZjA5ZTcyMzMtNmU1Nzc0MjAtOTIxNjAwLTE5M2VkZjJmZjMwMzAzIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiNjc2NDQxODczOCJ9%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%226764418738%22%7D%2C%22%24device_id%22%3A%22193edf2ff2f2ae-0194f6f09e7233-6e577420-921600-193edf2ff30303%22%7D", "domain": ".smzdm.com", "path": "/", "expires": 1797935976, "httpOnly": false, "secure": false}, {"sameSite": "Lax", "name": "_zdmA.time", "value": "1734863977201.0.https%3A%2F%2Fwww.smzdm.com%2F", "domain": ".www.smzdm.com", "path": "/", "expires": 1734866396, "httpOnly": false, "secure": false}], "local_storage": {"Hm_lvt_9b7ac3d38f30fe89ff0b8a0546904e58": "1766399975840|1734863945", "frameStatus": "collapse", "b00a7712533142fe89f4dcb5ef606f8b_u": "ddced709b80a7dc88952f4e1ca5ab5c6", "newGuideLayer": "1", "___ds_storage__search_isblock": "1|1734863949878"}, "headers": {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4595.0 Safari/537.36"}}'
    cookie_json = json.loads(cookie)
    cookies = cookie_json["cookies"]
    cookie_str = "; ".join([f"{cookie['name']}={cookie['value']}" for cookie in cookies])
    
    logger.add("smzdm.log", rotation="10 MB")
    
    # print(SMZDM(check_item={'cookie': cookie_str}).main())
    # SMZDM(check_item={'cookie': cookie_str}).do_sign_page_task()
    # activity_list = [str(i) for i in range(780, 831)]
    # SMZDM(check_item={'cookie': cookie_str}).do_activity_task(activity_list)
    # SMZDM(check_item={'cookie': cookie_str}).do_activity_task()
    # SMZDM(check_item={'cookie': cookie_str}).do_lottery()
    # activity_list = [str(i) for i in range(100472, 100502)]
    activity_list = ['gozz9w/248vt1', # 科沃斯618活动
                     '9bidsc/wsnjuv', # 25年618主会场
                     'myn92e/iup563', # 国补
                     'nnwzqc/bktxy2', # 618购物人格图鉴
                     'nosmzt/fcixoh', # 家的一万种可能-我家超智能
                     '100473'         # 618 | 我的购物车会说话！
                    ]
    # activity_list = [
    #                  '9bidsc/wsnjuv', # 25年618主会场
    #                 ]
    SMZDM(check_item={'cookie': cookie_str}).do_active(activity_list)
    # SMZDM(check_item={'cookie': cookie_str})._access_active_page('gozz9w/248vt1')
    