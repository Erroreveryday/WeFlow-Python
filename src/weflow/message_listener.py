import time
import threading
import logging
from datetime import datetime, timedelta
from .api_client import WeFlowAPIClient

class MessageListener:
    def __init__(self, api_client, talker, polling_interval=5, limit=50, start_date=None, start_days=7, aliyun_ai_client=None, history_count=20):
        self.api_client = api_client
        self.talker = talker
        self.polling_interval = polling_interval
        self.limit = limit
        self.start_date = start_date
        self.start_days = start_days
        self.aliyun_ai_client = aliyun_ai_client
        self.history_count = history_count
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
            # 只有当消息来自目标会话且不是首次启动时才调用AI
            # 首次启动时，last_message_time为0，只记录历史消息，不调用AI
            sender = message.get("senderUsername", "未知")
            if self.last_message_time > 0 and sender == self.talker:
                # 非首次启动且来自目标会话的消息，调用AI
                self._process_message(message, call_ai=True)
            else:
                # 首次启动或其他消息，只记录不调用AI
                self._process_message(message, call_ai=False)
        
        # 更新最后处理的消息时间
        if new_messages:
            self.last_message_time = new_messages[0].get("createTime", 0)
    
    def _get_history_messages(self):
        """获取历史消息"""
        # 计算日期范围
        end_date = datetime.now().strftime("%Y%m%d")
        
        if self.start_date:
            # 使用配置的开始日期
            start_date = self.start_date
        else:
            # 计算往前推指定天数的日期
            start_date = (datetime.now() - timedelta(days=self.start_days)).strftime("%Y%m%d")
        
        # 获取历史消息，使用较大的limit确保能获取足够的消息
        response = self.api_client.get_messages(
            talker=self.talker,
            limit=100,  # 使用更大的limit确保能获取足够的消息
            start=start_date,
            end=end_date
        )
        
        if not response or not response.get("success"):
            self.logger.error("获取历史消息失败")
            return []
        
        messages = response.get("messages", [])
        # 按时间戳排序，最新的消息在前面
        messages.sort(key=lambda x: x.get("createTime", 0), reverse=True)
        # 取最新的history_count条消息
        recent_messages = messages[:self.history_count]
        # 按时间戳正序排序，保持对话的时间顺序
        recent_messages.sort(key=lambda x: x.get("createTime", 0), reverse=False)
        return recent_messages
    
    def _process_message(self, message, call_ai=False):
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
        
        # 调用阿里云AI生成回复
        if call_ai and self.aliyun_ai_client:
            # 在后台线程中执行AI调用，避免阻塞轮询循环
            def call_ai_background():
                self.logger.info("正在调用阿里云AI生成回复...")
                # 获取历史消息
                history_messages = self._get_history_messages()
                
                # 构建消息格式
                messages = [
                    {"role": "system", "content": "你需要模拟'我'的身份和说话风格，基于历史聊天记录生成回复。\n\n角色：你就是'我'，需要以第一人称的方式直接回复消息。\n\n任务：分析历史聊天记录，理解对话上下文，然后以'我'的身份生成自然、符合语境的回复。\n\n风格要求：\n1. 保持语言风格一致，符合'我'的说话习惯\n2. 回复要自然、口语化，避免过于正式\n3. 基于上下文内容，不要偏离对话主题\n4. 回复长度要合理，不要过长或过短\n\n内容要求：\n1. 结合历史对话内容，保持连贯性\n2. 针对对方的问题或话题做出合理回应\n3. 可以包含适当的表情或语气词，使回复更生动\n4. 避免重复之前说过的内容\n\n请记住，你现在就是'我'，所有回复都要从'我'的角度出发。"}
                ]
                
                # 添加历史消息
                for msg in history_messages:
                    msg_sender = msg.get("senderUsername", "未知")
                    msg_content = msg.get("content", "")
                    # 确定消息角色
                    if msg_sender == self.talker:
                        # 假设talker是用户，AI是助手
                        role = "user"
                    else:
                        role = "assistant"
                    messages.append({"role": role, "content": msg_content})
                
                # 调用AI生成回复
                reply = self.aliyun_ai_client.generate_reply(messages)
                if reply:
                    self.logger.info(f"[AI] {reply}")
                else:
                    self.logger.warning("阿里云AI未生成回复")
            
            # 启动后台线程
            ai_thread = threading.Thread(target=call_ai_background)
            ai_thread.daemon = True
            ai_thread.start()
        
        # 可以在这里添加其他处理逻辑，比如发送通知、保存到数据库等
