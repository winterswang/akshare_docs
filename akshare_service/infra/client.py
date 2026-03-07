"""
基础客户端配置 (Infrastructure Client)
处理网络请求、代理和重试机制。
"""

import os
import functools
import logging
from typing import Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_proxies():
    """清除环境变量中的代理设置（可选，暂不强制执行）"""
    # proxies = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']
    # for p in proxies:
    #     if p in os.environ:
    #         logger.info(f"Clearing proxy env var: {p}")
    #         del os.environ[p]
    
    # os.environ['NO_PROXY'] = '*'
    pass

def robust_api(func):
    """装饰器：增强 API 调用的稳健性 (异常捕获)"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)
            logger.error(f"API Error in {func.__name__}: {error_msg}")
            
            # 识别特定错误并返回友好提示
            if "ProxyError" in error_msg:
                return None  # 或者抛出自定义 NetworkError
            if "KeyError" in error_msg:
                return None
            
            return None # 默认返回 None 表示失败
            
    return wrapper
