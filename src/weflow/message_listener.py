import time
import threading
import logging
from datetime import datetime, timedelta
from .api_client import WeFlowAPIClient

class MessageListener:
    def __init__(self, api_client, talker, polling_interval=5, limit=50, start_date=None, start_days=7):
        self.api_client = api_client
        self.talker = talker
        self.polling_interval = polling_interval
        self.limit = limit
        self.start_date = start_date
        self.start_days = start_days
        self.running = False
        self.thread = None
        self.last_message_time = 0
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """开始监听新消息"""
        if self.running:
            self.logger.warning("监听器已经在运行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._polling_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("消息监听器已启动")
    
    def stop(self):
        """停止监听新消息"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("消息监听器已停止")
    
    def _polling_loop(self):
        """轮询循环"""
        while self.running:
            try:
                self._check_new_messages()
            except Exception as e:
                self.logger.error(f"轮询过程中出错: {e}")
            time.sleep(self.polling_interval)
    
    def _check_new_messages(self):
        """检查新消息"""
        # 计算日期范围
        end_date = datetime.now().strftime("%Y%m%d")
        
        if self.start_date:
            # 使用配置的开始日期
            start_date = self.start_date
        else:
            # 计算往前推指定天数的日期
            start_date = (datetime.now() - timedelta(days=self.start_days)).strftime("%Y%m%d")
        
        # 记录日期范围
        self.logger.debug(f"日期范围: {start_date} 至 {end_date}")
        
        # 获取最新的消息
        response = self.api_client.get_messages(
            talker=self.talker,
            limit=self.limit,
            start=start_date,
            end=end_date
        )
        
        if not response or not response.get("success"):
            self.logger.error("获取消息失败")
            return
        
        messages = response.get("messages", [])
        if not messages:
            return
        
        # 按时间戳排序，最新的消息在前面
        messages.sort(key=lambda x: x.get("createTime", 0), reverse=True)
        
        # 处理新消息
        new_messages = []
        for message in messages:
            message_time = message.get("createTime", 0)
            if message_time > self.last_message_time:
                new_messages.append(message)
            else:
                break  # 因为已经排序，后面的消息时间更早
        
        # 处理新消息
        for message in reversed(new_messages):  # 按时间顺序处理
            self._process_message(message)
        
        # 更新最后处理的消息时间
        if new_messages:
            self.last_message_time = new_messages[0].get("createTime", 0)
    
    def _process_message(self, message):
        """处理新消息"""
        # 这里可以根据需要自定义消息处理逻辑
        sender = message.get("senderUsername", "未知")
        content = message.get("content", "")
        create_time = message.get("createTime", 0)
        # 尝试其他可能的时间戳字段名
        if create_time == 0:
            create_time = message.get("timestamp", 0)
        media_type = message.get("mediaType", "")
        
        # 打印原始时间戳值
        self.logger.debug(f"原始时间戳: {create_time}")
        
        # 格式化时间
        try:
            if create_time > 0:
                # 检查时间戳是否为毫秒级
                if create_time > 10**10:  # 大于 10^10 毫秒，约 30 年
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(create_time / 1000))
                else:
                    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(create_time))
            else:
                time_str = "未知时间"
        except Exception as e:
            self.logger.error(f"时间格式化出错: {e}")
            time_str = "时间格式错误"
        
        # 输出日志
        if media_type:
            self.logger.info(f"[{time_str}] {sender}: [{media_type}] {content}")
        else:
            self.logger.info(f"[{time_str}] {sender}: {content}")
        
        # 可以在这里添加其他处理逻辑，比如发送通知、保存到数据库等
