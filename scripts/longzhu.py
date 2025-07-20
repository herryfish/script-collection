# 标准库
import os
import json
import datetime
import sys
import random
import time

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
from utils.qlapi import QLApi
urllib3.disable_warnings()

# 配置日志输出
logger.remove()
logger.add(
    os.path.join(project_root, "logs", "longzhu_debug.log"),
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

APP = 'longzhu'

class longzhu:
    
    def __init__(self, account, app_configs, log_level='DEBUG'):
        self.session = requests.Session()
        self.user_token = account['token']
        self.app_configs = app_configs
        
        # 基础请求头
        base_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36 MicroMessenger/7.0.4.501 NetType/WIFI MiniProgramEnv/Windows WindowsWechat/WMPF',
            # 'User-Agent': 'Mozilla/5.0 (Linux; U; Android 2.3.6; zh-cn; GT-S5660 Build/GINGERBREAD) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1 MicroMessenger/4.5.255',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-us,en',
            'Referer': 'https://longzhu.longfor.com/longball-homeh5/'
        }
        
        # 认证请求头
        auth_headers = {
            'token': self.user_token,
            'X-LF-UserToken': self.user_token,
            'X-LF-Channel': app_configs['channel'],
            'X-LF-Bu-Code': app_configs['bu_code']
        }
        
        # 合并所有请求头
        self.session.headers.update(base_headers)
        self.session.headers.update(auth_headers)
        self.session.headers.update(app_configs['sign_in']['header'])

    def _signinV2(self, activity_no: str):
        url = 'https://longzhu.longfor.com/proxy/lmarketing-task-api-mvc-prod/openapi/task/v1/signature/clock'
        data = {"activity_no": activity_no}
        
        try:
            res = self.session.post(url, json=data, verify=False)
            res.raise_for_status()
            res_json = res.json()
            
            if res_json['code'] != '0000':
                error_msg = f"签到失败: {res_json.get('message', '未知错误')}"
                logger.error(error_msg)
                load_send(APP, error_msg)
                return False
                
            if res_json['data']['is_popup'] == 1:
                reward_info = res_json['data']['reward_info']
                logger.info(f"签到成功, 获得奖励: {reward_info}")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常: {str(e)}")
            load_send(APP, f"请求异常: {str(e)}")
            return False
        
        return False

    def signin(self):
        results = []
        for activity_no in self.app_configs['sign_in']['activity_no']:
            results.append(self._signinV2(activity_no))
        return all(results)

class longzhu_question(longzhu):
    
    def __init__(self, account, app_configs):
        super().__init__(account, app_configs)
        self.qlapi = QLApi()
        self.KEY = 'longzhu_question1'
        self.max_search_step = app_configs['question']['max_search_setp']
        self.session.headers.update(app_configs['question']['header'])
        logger.debug(f"初始化请求头: {self.session.headers}")

    def query_task(self, task_id: str) -> dict:
        """查询任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息的JSON响应
            
        Raises:
            requests.exceptions.RequestException: 请求异常时抛出
        """
        url = f'https://longzhu.longfor.com/proxy/lmarketing-task-api-prod/openapi/task/v1/information/list?task_id={task_id}'
        
        try:
            res = self.session.get(url, verify=False)
            res.raise_for_status()
            logger.debug(f"查询任务响应: {res.text}")
            return res.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"查询任务失败: {str(e)}")
            raise

    def answer(self, task_id: str, item_id: str, answer_num: int) -> bool:
        """回答问题
        
        Args:
            task_id: 任务ID
            item_id: 题目ID
            answer_num: 答案数量
            
        Returns:
            bool: 回答是否成功
        """
        url = 'https://longzhu.longfor.com/proxy/lmarketing-task-api-prod/openapi/task/v1/information/user'
        
        # 随机选择答案
        user_answer = [0] * answer_num
        rand_num = random.randint(0, answer_num - 1)
        user_answer[rand_num] = 1

        data = {
            "token": self.user_token,
            "channel": self.app_configs['channel'],
            "bu_code": self.app_configs['bu_code'],
            "task_id": task_id,
            "item_id": item_id,
            "item_content": json.dumps({"user_answer": user_answer})
        }

        try:
            res = self.session.post(url, json=data, verify=False)
            res.raise_for_status()
            logger.debug(f"回答问题响应: {res.text}")
            ret_json = res.json()
            if ret_json.get('code') == '0000':
                logger.info(f"回答问题结果：{ret_json.get('data')}")
                return True
            else:
                logger.error(f"回答问题失败: {ret_json.get('message')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"回答问题失败: {str(e)}")
            return False

    def count_days_to_now(self, start_datetime_str: str) -> int:
        """计算从指定日期到现在的天数
        
        Args:
            start_datetime_str: 起始日期字符串(YYYY-MM-DD)
            
        Returns:
            int: 天数差
        """
        try:
            start_datetime = datetime.datetime.strptime(start_datetime_str, "%Y-%m-%d")
            return (datetime.datetime.now() - start_datetime).days
        except ValueError as e:
            logger.error(f"日期格式错误: {str(e)}")
            return 0

    def is_today(self, date_str: str) -> bool:
        """判断日期是否为今天
        
        Args:
            date_str: 日期字符串(YYYY-MM-DD)
            
        Returns:
            bool: 是否为今天
        """
        try:
            input_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            return input_date == datetime.datetime.now().date()
        except ValueError as e:
            logger.error(f"日期格式错误: {str(e)}")
            return False
    
    def main(self) -> bool:
        """主执行方法
        
        Returns:
            bool: 是否成功执行所有任务
        """
        try:
            env_value = self.qlapi.get_env(self.KEY)
            json_str = json.loads(env_value['value'])
            logger.debug(f"环境变量值: {json_str}")
            
            task_id = json_str['task_id'] if self.is_today(json_str['date']) else \
                     json_str['task_id'] + self.count_days_to_now(json_str['date'])
            
            logger.info(f"当前任务ID: {task_id}")
            
            success = False
            step = 0
            
            while not success and step <= self.max_search_step:
                try:
                    ret = self.query_task(task_id)
                    
                    if ret['code'] == '0000':
                        success = True
                        today_str = datetime.datetime.now().strftime('%Y-%m-%d')
                        
                        for item in ret['data']['information']:
                            if item['status'] == 0:
                                answers = json.loads(item['content'])
                                logger.info(f'执行任务 {item["item_id"]}:{item["name"]}({len(answers["answer"])})')
                                # 输出答案选项
                                for i, answer_item in enumerate(answers["answer"]):
                                    logger.info(f"答案选项 {i+1}: {answer_item}")
                                if not self.answer(task_id, item['item_id'], len(answers['answer'])):
                                    return False
                                
                                if not self.is_today(json_str['date']):
                                    self.qlapi.edit_env(self.KEY, json.dumps({
                                        "date": today_str, 
                                        "task_id": task_id
                                    }))
                            else:
                                logger.warning(f'任务 {item["name"]} 已完成')
                        
                        return True
                    
                    elif (not self.is_today(json_str['date'])) and (ret['code'] in ('801902', '801905')):
                        step += 1
                        task_id += 1
                        logger.info(f"尝试新任务ID: {task_id}")
                    else:
                        logger.error(f"任务查询失败: {ret.get('message', '未知错误')}")
                        load_send(APP, ret.get('message', '任务查询失败'))
                        return False
                        
                except Exception as e:
                    logger.error(f"处理任务异常: {str(e)}")
                    return False
            
            if step > self.max_search_step:
                logger.warning('无法找到新的问题')
                load_send(APP, '无法找到新的问题')
                
            return False
            
        except Exception as e:
            logger.error(f"主流程异常: {str(e)}")
            return False

class longzhu_lottery(longzhu):
    
    def __init__(self, account, app_configs):
        super().__init__(account, app_configs)
        
        # 更新抽奖特定请求头
        self.session.headers.update(app_configs['lottery']['header'])
        
        # 设置认证相关请求头
        lottery_headers = {
            'authtoken': self.user_token,
            'channel': self.app_configs['channel'],
            'bucode': self.app_configs['bu_code']
        }
        self.session.headers.update(lottery_headers)
        
        # 移除不需要的请求头
        headers_to_remove = ['token', 'X-LF-UserToken', 'X-LF-Channel', 'X-LF-Bu-Code']
        for header in headers_to_remove:
            if header in self.session.headers:
                del self.session.headers[header]
                
        logger.debug(f"抽奖请求头: {self.session.headers}")
    
    def lottery_sign(self) -> int:
        """签到获取抽奖机会
        
        Returns:
            int: 获得的抽奖机会数量，失败返回0
        """
        url = 'https://gw2c-hw-open.longfor.com/llt-gateway-prod/api/v1/activity/auth/lottery/sign'
        
        try:
            res = self.session.post(url, json=self.app_configs['lottery']['lottery_data'], verify=False)
            res.raise_for_status()
            res_json = res.json()
            
            if res_json['code'] != '0000':
                logger.warning(f"签到失败: {res_json.get('message', '未知错误')}")
                load_send(APP, res_json.get('message', '签到失败'))
                return 0
                
            logger.info(f"签到成功，获得抽奖机会: {res_json['data']['chance']}")
            return res_json['data']['chance']
            
        except requests.exceptions.RequestException as e:
            logger.error(f"签到请求异常: {str(e)}")
            load_send(APP, f"签到请求异常: {str(e)}")
            return 0
    
    def lottery_click(self) -> bool:
        """执行抽奖
        
        Returns:
            bool: 抽奖是否成功
        """
        url = 'https://gw2c-hw-open.longfor.com/llt-gateway-prod/api/v1/activity/auth/lottery/click'
        
        try:
            res = self.session.post(url, json=self.app_configs['lottery']['lottery_data'], verify=False)
            res.raise_for_status()
            res_json = res.json()
            
            if res_json['code'] != '0000':
                logger.warning(f"抽奖失败: {res_json.get('message', '未知错误')}")
                load_send(APP, res_json.get('message', '抽奖失败'))
                return False
                
            logger.info(f"抽奖成功: {res_json['data']}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"抽奖请求异常: {str(e)}")
            load_send(APP, f"抽奖请求异常: {str(e)}")
            return False
    
    def main(self) -> bool:
        """主执行方法
        
        Returns:
            bool: 是否成功执行签到和抽奖
        """
        try:
            if self.lottery_sign() > 0:
                time.sleep(1)  # 避免请求过于频繁
                return self.lottery_click()
            return False
        except Exception as e:
            logger.error(f"抽奖主流程异常: {str(e)}")
            return False

if __name__ == "__main__":

    accounts = get_user_infos(APP)
    app_configs = get_app_configs(APP)
    if not accounts:
        logger.error("未找到有效的账户配置信息")
        exit(1)

    for account in accounts:
        # 暂时无法支持多个ID，会出现滑块验证
        longzhu(account, app_configs).signin() 
        time.sleep(2)
        longzhu_lottery(account, app_configs).main()
        time.sleep(2)
        longzhu_question(account, app_configs).main()