import requests
import time
import logging
import sys
import os
from typing import Dict, List, Callable, Optional
from datetime import datetime
from PyQt5.QtCore import QThread, pyqtSignal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MessageListenerThread(QThread):
    """
    会话消息监听器线程
    在独立线程中运行，不阻塞 GUI
    """
    
    new_message = pyqtSignal(dict, dict)
    
    def __init__(self, check_interval: int = 1, base_url: Optional[str] = None):
        """
        初始化监听器线程
        
        Args:
            check_interval: 检查间隔时间（秒），默认 1 秒
            base_url: WeFlow API 基础地址，默认从配置文件读取
        """
        super().__init__()
        self.check_interval = check_interval
        self.base_url = base_url
        self.last_messages: Dict[str, Dict] = {}
        self.is_running = False
        self.enabled_sessions: List[Dict] = []
        
        self._init_config()
    
    def _init_config(self):
        """初始化配置"""
        config = load_config()
        port = config.get('weflow_api_port', 5031)
        self.base_url = self.base_url or f"http://127.0.0.1:{port}"
        self._load_enabled_sessions(config)
        logger.info(f"监听器线程初始化完成，API地址: {self.base_url}")
    
    def _load_enabled_sessions(self, config: Dict):
        """从配置文件加载启用的会话"""
        self.enabled_sessions = []
        sessions = config.get('wechat_sessions', [])
        
        for session in sessions:
            if session.get('auto_reply', False):
                wechat_id = session.get('wechat_id', '')
                if wechat_id:
                    self.enabled_sessions.append(session)
                    logger.info(f"启用监听会话: {session.get('contact_remark', wechat_id)} ({wechat_id})")
        
        logger.info(f"共启用 {len(self.enabled_sessions)} 个会话监听")
    
    def _get_latest_message(self, talker: str) -> Optional[Dict]:
        """
        获取指定会话的最新消息
        
        Args:
            talker: 会话 ID
        
        Returns:
            最新消息字典，如果获取失败返回 None
        """
        try:
            params = {
                'talker': talker,
                'limit': 1
            }
            
            response = requests.get(
                f"{self.base_url}/api/v1/messages",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('messages'):
                    return data['messages'][0]
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取消息失败 ({talker}): {e}")
            return None
    
    def _check_new_messages(self):
        """检查所有启用会话的新消息"""
        for session in self.enabled_sessions:
            talker = session.get('wechat_id', '')
            if not talker:
                continue
            
            latest_message = self._get_latest_message(talker)
            
            if not latest_message:
                continue
            
            message_id = latest_message.get('localId')
            
            if talker not in self.last_messages:
                self.last_messages[talker] = latest_message
                logger.info(f"初始化会话 {talker} 的最新消息 ID: {message_id}")
                continue
            
            last_message_id = self.last_messages[talker].get('localId')
            
            if message_id > last_message_id:
                logger.info(f"检测到新消息！会话: {talker}, 消息 ID: {message_id}")
                
                self.last_messages[talker] = latest_message
                
                self.new_message.emit(session, latest_message)
    
    def run(self):
        """线程运行方法"""
        self.is_running = True
        logger.info("开始监听新消息...")
        
        while self.is_running:
            try:
                self._check_new_messages()
            except Exception as e:
                logger.error(f"检查新消息时发生错误: {e}")
            
            time.sleep(self.check_interval)
    
    def stop(self):
        """停止监听"""
        self.is_running = False
        self.wait()
        logger.info("停止监听新消息")
    
    def reload_config(self):
        """重新加载配置文件"""
        config = load_config()
        self._load_enabled_sessions(config)
        port = config.get('weflow_api_port', 5031)
        self.base_url = f"http://127.0.0.1:{port}"
        # 清空历史消息记录，以便重新初始化监听的会话
        self.last_messages = {}
        logger.info("配置已重新加载，历史消息记录已清空")


class MessageListener:
    """
    会话消息监听器
    监听配置文件中启用的会话（auto_reply: true），检测新消息并触发回调
    """

    def __init__(self, check_interval: int = 5, base_url: Optional[str] = None):
        """
        初始化监听器

        Args:
            check_interval: 检查间隔时间（秒），默认 5 秒
            base_url: WeFlow API 基础地址，默认从配置文件读取
        """
        self.check_interval = check_interval
        self.base_url = base_url
        self.last_messages: Dict[str, Dict] = {}
        self.is_running = False
        self.message_callbacks: List[Callable] = []
        self.enabled_sessions: List[Dict] = []
        
        self._init_config()

    def _init_config(self):
        """初始化配置"""
        config = load_config()
        port = config.get('weflow_api_port', 5031)
        self.base_url = self.base_url or f"http://127.0.0.1:{port}"
        self._load_enabled_sessions(config)
        logger.info(f"监听器初始化完成，API地址: {self.base_url}")

    def _load_enabled_sessions(self, config: Dict):
        """从配置文件加载启用的会话"""
        self.enabled_sessions = []
        sessions = config.get('wechat_sessions', [])
        
        for session in sessions:
            if session.get('auto_reply', False):
                wechat_id = session.get('wechat_id', '')
                if wechat_id:
                    self.enabled_sessions.append(session)
                    logger.info(f"启用监听会话: {session.get('contact_remark', wechat_id)} ({wechat_id})")
        
        logger.info(f"共启用 {len(self.enabled_sessions)} 个会话监听")

    def _get_latest_message(self, talker: str) -> Optional[Dict]:
        """
        获取指定会话的最新消息

        Args:
            talker: 会话 ID

        Returns:
            最新消息字典，如果获取失败返回 None
        """
        try:
            params = {
                'talker': talker,
                'limit': 1
            }
            
            response = requests.get(
                f"{self.base_url}/api/v1/messages",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('messages'):
                    return data['messages'][0]
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取消息失败 ({talker}): {e}")
            return None

    def _check_new_messages(self):
        """检查所有启用会话的新消息"""
        for session in self.enabled_sessions:
            talker = session.get('wechat_id', '')
            if not talker:
                continue
            
            latest_message = self._get_latest_message(talker)
            
            if not latest_message:
                continue
            
            message_id = latest_message.get('localId')
            
            if talker not in self.last_messages:
                self.last_messages[talker] = latest_message
                logger.info(f"初始化会话 {talker} 的最新消息 ID: {message_id}")
                continue
            
            last_message_id = self.last_messages[talker].get('localId')
            
            if message_id > last_message_id:
                logger.info(f"检测到新消息！会话: {talker}, 消息 ID: {message_id}")
                
                self.last_messages[talker] = latest_message
                
                self._trigger_callbacks(session, latest_message)

    def _trigger_callbacks(self, session: Dict, message: Dict):
        """
        触发所有注册的回调函数

        Args:
            session: 会话信息
            message: 新消息内容
        """
        for callback in self.message_callbacks:
            try:
                callback(session, message)
            except Exception as e:
                logger.error(f"回调函数执行失败: {e}")

    def add_callback(self, callback: Callable):
        """
        添加新消息回调函数

        Args:
            callback: 回调函数，接收两个参数 (session, message)
        """
        self.message_callbacks.append(callback)
        logger.info(f"已添加回调函数，当前共有 {len(self.message_callbacks)} 个回调")

    def remove_callback(self, callback: Callable):
        """
        移除回调函数

        Args:
            callback: 要移除的回调函数
        """
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
            logger.info(f"已移除回调函数，当前共有 {len(self.message_callbacks)} 个回调")

    def start(self):
        """启动监听"""
        if self.is_running:
            logger.warning("监听器已在运行中")
            return
        
        self.is_running = True
        logger.info("开始监听新消息...")
        
        while self.is_running:
            try:
                self._check_new_messages()
            except Exception as e:
                logger.error(f"检查新消息时发生错误: {e}")
            
            time.sleep(self.check_interval)

    def stop(self):
        """停止监听"""
        self.is_running = False
        logger.info("停止监听新消息")

    def reload_config(self):
        """重新加载配置文件"""
        config = load_config()
        self._load_enabled_sessions(config)
        port = config.get('weflow_api_port', 5031)
        self.base_url = f"http://127.0.0.1:{port}"
        logger.info("配置已重新加载")


def example_callback(session: Dict, message: Dict):
    """
    示例回调函数
    
    Args:
        session: 会话信息
        message: 新消息内容
    """
    contact_remark = session.get('contact_remark', '未知')
    content = message.get('content', '')
    sender = message.get('senderUsername', '')
    create_time = message.get('createTime', 0)
    
    timestamp = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info(f"=== 新消息通知 ===")
    logger.info(f"会话: {contact_remark}")
    logger.info(f"发送者: {sender}")
    logger.info(f"时间: {timestamp}")
    logger.info(f"内容: {content}")
    logger.info(f"==================")


if __name__ == "__main__":
    listener = MessageListener(check_interval=5)
    
    listener.add_callback(example_callback)
    
    try:
        listener.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止监听")
        listener.stop()