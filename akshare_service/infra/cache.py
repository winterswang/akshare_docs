"""
缓存基础设施 (Cache Infrastructure)
提供本地文件缓存功能，减少 API 重复请求
"""

import os
import json
import hashlib
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta


class LocalCache:
    """本地文件缓存"""
    
    def __init__(self, cache_dir: str = "/tmp/akshare_cache", default_ttl: int = 3600):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
            default_ttl: 默认过期时间（秒），默认 1 小时
        """
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, key: str) -> str:
        """生成缓存文件名"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """获取缓存数据"""
        cache_file = self._get_cache_key(key)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            expired_at = cached.get('expired_at')
            if expired_at and datetime.fromisoformat(expired_at) < datetime.now():
                os.remove(cache_file)
                return None
            
            return cached.get('data')
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def set(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """设置缓存数据"""
        cache_file = self._get_cache_key(key)
        ttl = ttl or self.default_ttl
        
        cache_data = {
            'data': data,
            'expired_at': (datetime.now() + timedelta(seconds=ttl)).isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False)
    
    def delete(self, key: str) -> None:
        """删除缓存"""
        cache_file = self._get_cache_key(key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
    
    def clear_expired(self) -> int:
        """清理过期缓存"""
        count = 0
        if not os.path.exists(self.cache_dir):
            return count
        
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                
                expired_at = cached.get('expired_at')
                if expired_at and datetime.fromisoformat(expired_at) < datetime.now():
                    os.remove(filepath)
                    count += 1
            except:
                pass
        
        return count


# 全局缓存实例
_cache_instance: Optional[LocalCache] = None


def get_cache() -> LocalCache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache()
    return _cache_instance


if __name__ == '__main__':
    cache = LocalCache()
    cache.set("test", {"value": 123}, ttl=60)
    print(cache.get("test"))