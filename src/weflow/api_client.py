import requests
import logging

class WeFlowAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def health_check(self):
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"健康检查失败: {e}")
            return None
    
    def get_messages(self, talker, limit=100, offset=0, start=None, end=None, 
                    keyword=None, chatlab=None, format=None, media=0, 
                    image=None, voice=None, video=None, emoji=None):
        """获取消息列表"""
        try:
            params = {
                "talker": talker,
                "limit": limit,
                "offset": offset
            }
            
            if start:
                params["start"] = start
            if end:
                params["end"] = end
            if keyword:
                params["keyword"] = keyword
            if chatlab:
                params["chatlab"] = chatlab
            if format:
                params["format"] = format
            if media:
                params["media"] = media
            if image is not None:
                params["image"] = image
            if voice is not None:
                params["voice"] = voice
            if video is not None:
                params["video"] = video
            if emoji is not None:
                params["emoji"] = emoji
            
            response = requests.get(f"{self.base_url}/api/v1/messages", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"获取消息失败: {e}")
            return None
    
    def get_sessions(self, keyword=None, limit=100):
        """获取会话列表"""
        try:
            params = {}
            if keyword:
                params["keyword"] = keyword
            if limit:
                params["limit"] = limit
            
            response = requests.get(f"{self.base_url}/api/v1/sessions", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"获取会话列表失败: {e}")
            return None
    
    def get_contacts(self, keyword=None, limit=100):
        """获取联系人列表"""
        try:
            params = {}
            if keyword:
                params["keyword"] = keyword
            if limit:
                params["limit"] = limit
            
            response = requests.get(f"{self.base_url}/api/v1/contacts", params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"获取联系人列表失败: {e}")
            return None