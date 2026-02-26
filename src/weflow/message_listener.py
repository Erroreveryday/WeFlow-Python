import time
import threading
import logging
from datetime import datetime, timedelta
from .api_client import WeFlowAPIClient
from .keyboard_automation import KeyboardAutomation

class MessageListener:
    def __init__(self, api_client, talker, polling_interval=5, limit=50, start_date=None, start_days=7, aliyun_ai_client=None, history_count=20, config=None, target_session=None):
        self.api_client = api_client
        self.talker = talker
        self.polling_interval = polling_interval
        self.limit = limit
        self.start_date = start_date
        self.start_days = start_days
        self.aliyun_ai_client = aliyun_ai_client
        self.history_count = history_count
        self.config = config
        self.target_session = target_session
        self.running = False
        self.thread = None
        self.last_message_time = 0
        self.logger = logging.getLogger(__name__)
        # 初始化键盘自动化实例
        if config:
            self.keyboard_automation = KeyboardAutomation(config)
        else:
            self.keyboard_automation = None
    
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
                    {"role": "system", "content": "你是'我'，以第一人称回复消息。基于历史聊天记录理解上下文，直接生成符合'我'说话风格的自然回复。\n\n其他用户消息格式为 [用户标识] 内容，仅用于区分用户，回复中绝对不要使用这些标识。\n\n要求：口语化、符合语境、连贯回应、适当表情、避免重复。\n\n记住：你就是'我'，只针对消息内容回复，不要使用用户标识。"}
                ]
                
                # 添加历史消息
                for msg in history_messages:
                    msg_sender = msg.get("senderUsername", "未知")
                    msg_content = msg.get("content", "")
                    # 确定消息角色和内容格式
                    if msg_sender == self.talker:
                        # 假设talker是用户，AI是助手
                        role = "user"
                        # 对于用户消息，直接使用内容
                        formatted_content = msg_content
                    else:
                        role = "assistant"
                        # 对于其他用户消息，添加用户名标识
                        formatted_content = f"[{msg_sender}] {msg_content}"
                    messages.append({"role": role, "content": formatted_content})
                
                # 输出调试信息，显示发送给AI的完整消息
                self.logger.debug(f"发送给AI的消息内容: {messages}")
                
                # 调用AI生成回复
                reply = self.aliyun_ai_client.generate_reply(messages)
                if reply:
                    # 清理回复中的用户标识前缀
                    # 移除类似 [wxid_xxx] 这样的前缀
                    import re
                    cleaned_reply = re.sub(r'^\[wxid_\w+\]\s*', '', reply)
                    self.logger.info(f"[AI] 原始回复: {reply}")
                    self.logger.info(f"[AI] 清理后回复: {cleaned_reply}")
                    # 使用键盘自动化发送消息到微信
                    if self.keyboard_automation and self.target_session:
                        self.logger.info(f"正在发送消息到微信会话: {self.target_session}")
                        success = self.keyboard_automation.send_message(cleaned_reply, self.target_session)
                        if success:
                            self.logger.info("消息发送成功")
                        else:
                            self.logger.error("消息发送失败")
                    else:
                        self.logger.warning("键盘自动化未初始化或目标会话未设置")
                else:
                    self.logger.warning("阿里云AI未生成回复")
            
            # 启动后台线程
            ai_thread = threading.Thread(target=call_ai_background)
            ai_thread.daemon = True
            ai_thread.start()
        
        # 可以在这里添加其他处理逻辑，比如发送通知、保存到数据库等