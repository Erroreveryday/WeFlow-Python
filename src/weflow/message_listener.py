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
    new_message = pyqtSignal(dict, dict)
    message_processed = pyqtSignal(str, dict)

    def __init__(self, check_interval: int = 1, base_url: Optional[str] = None):
        super().__init__()
        self.check_interval = check_interval
        self.base_url = base_url
        self.last_messages: Dict[str, Dict] = {}
        self.last_timestamps: Dict[str, int] = {}
        self.is_running = False
        self.enabled_sessions: List[Dict] = []
        self.processed_messages: set = set()
        
        self._init_config()
    
    def _init_config(self):
        config = load_config()
        port = config.get('weflow_api_port', 5031)
        self.base_url = self.base_url or f"http://127.0.0.1:{port}"
        self._load_enabled_sessions(config)
        logger.info(f"监听器线程初始化完成，API地址: {self.base_url}")
    
    def _load_enabled_sessions(self, config: Dict):
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
    
    def _is_new_message(self, talker: str, message: Dict) -> bool:
        message_id = message.get('localId')
        message_time = message.get('createTime', 0)
        
        if message_id in self.processed_messages:
            return False
        
        last_time = self.last_timestamps.get(talker, 0)
        
        if message_time > last_time:
            # 即使是第一次收到消息，只要是新消息就返回True
            self.last_timestamps[talker] = message_time
            self.last_messages[talker] = message
            self.processed_messages.add(message_id)
            logger.info(f"初始化会话 {talker} 的最新消息，时间戳: {message_time}")
            return True
        
        return False
    
    def _check_new_messages(self):
        for session in self.enabled_sessions:
            talker = session.get('wechat_id', '')
            if not talker:
                continue
            
            latest_message = self._get_latest_message(talker)
            
            if not latest_message:
                continue
            
            # 检查消息发送者是否是指定会话的对方ID
            sender = latest_message.get('senderUsername', '')
            if sender != talker:
                logger.info(f"忽略消息：发送者 {sender} 不是指定会话的对方ID {talker}")
                continue
            
            message_id = latest_message.get('localId')
            message_time = latest_message.get('createTime', 0)
            
            if self._is_new_message(talker, latest_message):
                logger.info(f"检测到新消息！会话: {talker}, 消息ID: {message_id}, 时间戳: {message_time}")
                
                self.last_messages[talker] = latest_message
                self.last_timestamps[talker] = message_time
                self.processed_messages.add(message_id)
                
                if len(self.processed_messages) > 1000:
                    self.processed_messages = set(list(self.processed_messages)[-500:])
                
                self.new_message.emit(session, latest_message)
                self.message_processed.emit(talker, latest_message)
    
    def run(self):
        self.is_running = True
        logger.info("开始监听新消息...")
        
        while self.is_running:
            try:
                self._check_new_messages()
            except Exception as e:
                logger.error(f"检查新消息时发生错误: {e}")
            
            time.sleep(self.check_interval)
    
    def stop(self):
        self.is_running = False
        self.wait()
        logger.info("停止监听新消息")
    
    def stop_non_blocking(self):
        """非阻塞方式停止线程"""
        self.is_running = False
        # 不调用 wait()，让线程自行结束
        logger.info("停止监听新消息（非阻塞）")
    
    def reload_config(self):
        config = load_config()
        self._load_enabled_sessions(config)
        port = config.get('weflow_api_port', 5031)
        self.base_url = f"http://127.0.0.1:{port}"
        self.last_messages = {}
        self.last_timestamps = {}
        self.processed_messages = set()
        logger.info("配置已重新加载，历史消息记录已清空")

    def update_processed_message(self, talker: str, message_id: int, message_time: int):
        """
        更新已处理消息记录，防止重复处理同一条消息
        """
        if talker not in self.last_timestamps:
            self.last_timestamps[talker] = message_time
        
        if message_time >= self.last_timestamps.get(talker, 0):
            self.last_timestamps[talker] = message_time
        
        self.processed_messages.add(message_id)
        
        if talker in self.last_messages:
            last_msg = self.last_messages[talker]
            if last_msg.get('localId') != message_id:
                self.last_messages[talker] = {'localId': message_id, 'createTime': message_time}


class MessageListener:
    def __init__(self, check_interval: int = 5, base_url: Optional[str] = None):
        self.check_interval = check_interval
        self.base_url = base_url
        self.last_messages: Dict[str, Dict] = {}
        self.last_timestamps: Dict[str, int] = {}
        self.is_running = False
        self.message_callbacks: List[Callable] = []
        self.enabled_sessions: List[Dict] = []
        self.processed_messages: set = set()
        
        self._init_config()

    def _init_config(self):
        config = load_config()
        port = config.get('weflow_api_port', 5031)
        self.base_url = self.base_url or f"http://127.0.0.1:{port}"
        self._load_enabled_sessions(config)
        logger.info(f"监听器初始化完成，API地址: {self.base_url}")

    def _load_enabled_sessions(self, config: Dict):
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

    def _is_new_message(self, talker: str, message: Dict) -> bool:
        message_id = message.get('localId')
        message_time = message.get('createTime', 0)
        
        if message_id in self.processed_messages:
            return False
        
        last_time = self.last_timestamps.get(talker, 0)
        
        if message_time > last_time:
            # 即使是第一次收到消息，只要是新消息就返回True
            self.last_timestamps[talker] = message_time
            self.last_messages[talker] = message
            self.processed_messages.add(message_id)
            logger.info(f"初始化会话 {talker} 的最新消息，时间戳: {message_time}")
            return True
        
        return False

    def _check_new_messages(self):
        for session in self.enabled_sessions:
            talker = session.get('wechat_id', '')
            if not talker:
                continue
            
            latest_message = self._get_latest_message(talker)
            
            if not latest_message:
                continue
            
            # 检查消息发送者是否是指定会话的对方ID
            sender = latest_message.get('senderUsername', '')
            if sender != talker:
                logger.info(f"忽略消息：发送者 {sender} 不是指定会话的对方ID {talker}")
                continue
            
            message_id = latest_message.get('localId')
            message_time = latest_message.get('createTime', 0)
            
            if self._is_new_message(talker, latest_message):
                logger.info(f"检测到新消息！会话: {talker}, 消息ID: {message_id}, 时间戳: {message_time}")
                
                self.last_messages[talker] = latest_message
                self.last_timestamps[talker] = message_time
                self.processed_messages.add(message_id)
                
                if len(self.processed_messages) > 1000:
                    self.processed_messages = set(list(self.processed_messages)[-500:])
                
                self._trigger_callbacks(session, latest_message)

    def _trigger_callbacks(self, session: Dict, message: Dict):
        for callback in self.message_callbacks:
            try:
                callback(session, message)
            except Exception as e:
                logger.error(f"回调函数执行失败: {e}")

    def add_callback(self, callback: Callable):
        self.message_callbacks.append(callback)
        logger.info(f"已添加回调函数，当前共有 {len(self.message_callbacks)} 个回调")

    def remove_callback(self, callback: Callable):
        if callback in self.message_callbacks:
            self.message_callbacks.remove(callback)
            logger.info(f"已移除回调函数，当前共有 {len(self.message_callbacks)} 个回调")

    def start(self):
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
        self.is_running = False
        logger.info("停止监听新消息")

    def reload_config(self):
        config = load_config()
        self._load_enabled_sessions(config)
        port = config.get('weflow_api_port', 5031)
        self.base_url = f"http://127.0.0.1:{port}"
        self.last_messages = {}
        self.last_timestamps = {}
        self.processed_messages = set()
        logger.info("配置已重新加载")


def example_callback(session: Dict, message: Dict):
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