import requests
from typing import Optional, Dict, Any
from loguru import logger
import time
from utils.config import get_common_settings

class QLApi:
    """青龙面板 API 客户端"""
    
    def __init__(self):
        """初始化青龙API客户端，从配置文件加载青龙面板配置"""
        # 从配置文件加载青龙面板配置
        ql_config = get_common_settings('qinglong')
        
        self.session = requests.Session()
        self.ql_host = ql_config.get('host', 'localhost:5700')
        self.client_id = ql_config.get('client_id', '')
        self.client_secret = ql_config.get('client_secret', '')
        self.token: Optional[str] = None
        
        # 设置请求超时和重试
        self.session.timeout = 10
        self.max_retries = 3
        self.retry_delay = 5
        
        # 设置通用请求头
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QL-API-Client/1.0'
        })

    def _make_request(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求并处理响应
        
        Args:
            method: HTTP 方法
            url: 请求URL
            **kwargs: 请求参数
            
        Returns:
            Dict: API 响应数据
            
        Raises:
            Exception: 当请求失败或响应无效时抛出
        """
        if self.token:
            kwargs.setdefault('headers', {})['Authorization'] = self.token
            
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.retry_delay)

    def get_env(self, key: str) -> Optional[Dict[str, Any]]:
        """获取环境变量
        
        Args:
            key: 环境变量名称
            
        Returns:
            Optional[Dict]: 环境变量信息，未找到时返回 None
        """
        if not self.token:
            self.client_token()
            
        url = f'http://{self.ql_host}/open/envs'
        response = self._make_request('GET', url)
        
        if not response.get('data'):
            logger.warning(f"No environment variables found for key: {key}")
            return None
            
        for env_data in response['data']:
            if env_data.get('name') == key:
                return env_data
        return None

    def edit_env(self, key: str, value: str) -> bool:
        """编辑环境变量
        
        Args:
            key: 环境变量名称
            value: 新的值
            
        Returns:
            bool: 更新是否成功
        """
        old_data = self.get_env(key)
        if not old_data:
            logger.error(f"Environment variable not found: {key}")
            return False

        new_data = {
            'name': old_data['name'],
            'value': value,
            'remarks': old_data.get('remarks', ''),
            'id': old_data['id']
        }

        # 使用本地时间戳替代 get_timestamp
        timestamp = int(time.time() * 1000)  # 获取毫秒级时间戳
        url = f'http://{self.ql_host}/open/envs?t={timestamp}'
        try:
            response = self._make_request('PUT', url, json=new_data)
            success = response.get('code') == 200
            if success:
                logger.info(f"Successfully updated environment variable: {key}")
            else:
                logger.error(f"Failed to update environment variable: {key}")
            return success
        except Exception as e:
            logger.error(f"Error updating environment variable: {str(e)}")
            return False

    def client_token(self) -> bool:
        """获取访问令牌
        
        Returns:
            bool: 是否成功获取令牌
        """
        url = (f'http://{self.ql_host}/open/auth/token'
               f'?client_id={self.client_id}&client_secret={self.client_secret}')
        try:
            response = self._make_request('GET', url)
            if response.get('code') == 200:
                token_data = response['data']
                self.token = f"{token_data['token_type']} {token_data['token']}"
                logger.debug("Successfully obtained new token")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to obtain token: {str(e)}")
            return False

def test():
    """测试 QLApi 功能"""
    key = 'test'
    qlapi = QLApi()
    
    if not qlapi.client_token():
        logger.error("Failed to obtain token")
        return
        
    env_data = qlapi.get_env(key)
    logger.info(f"Current env data: {env_data}")
    
    if qlapi.edit_env(key, key):
        logger.info("Successfully updated test environment variable")
    else:
        logger.error("Failed to update test environment variable")        

if __name__ == "__main__":
    test()