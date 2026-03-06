import requests
import logging
import json
import os
from typing import List, Dict, Optional, Callable
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """DeepSeek API 客户端"""

    def __init__(self, api_key: str, model: str = "deepseek-chat", base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"DeepSeek 客户端初始化完成，模型: {model}")
    
    def get_recent_messages(self, base_url: str, talker: str, limit: int = 10) -> List[Dict]:
        """
        从 WeFlow 获取指定会话的最近消息
        
        Args:
            base_url: WeFlow API 基础 URL
            talker: 会话 ID
            limit: 获取消息数量
        
        Returns:
            消息列表
        """
        logger.info(f"开始获取会话 {talker} 的最近 {limit} 条消息...")
        try:
            params = {
                'talker': talker,
                'limit': limit
            }
            
            response = requests.get(
                f"{base_url}/api/v1/messages",
                params=params,
                timeout=10
            )
            
            logger.info(f"请求状态码: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('messages'):
                    messages = data['messages']
                    messages.sort(key=lambda x: x.get('createTime', 0))
                    logger.info(f"成功获取 {len(messages)} 条消息")
                    return messages
                else:
                    logger.error(f"API 响应异常: {data}")
                    return []
            else:
                logger.error(f"API 请求失败，状态码: {response.status_code}")
                return []
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求异常: {str(e)}")
            return []
    
    def format_messages_for_deepseek(self, messages: List[Dict], talker: str) -> List[Dict]:
        """
        格式化消息为 DeepSeek API 所需的格式
        
        Args:
            messages: 原始消息列表
            talker: 对方 ID
        
        Returns:
            格式化后的消息列表
        """
        formatted_messages = []
        
        for msg in messages:
            sender = msg.get('senderUsername', '')
            is_self = sender != talker
            
            content = msg.get('content', '')
            if msg.get('mediaType'):
                media_type = msg.get('mediaType')
                content = f"[{media_type.upper()}] {content}"
            
            formatted_msg = {
                "role": "assistant" if is_self else "user",
                "content": content
            }
            
            formatted_messages.append(formatted_msg)
        
        return formatted_messages
    
    def build_system_prompt(self, session: Dict, default_system_prompt: str = "你模拟我与对方聊天。") -> str:
        """
        构建系统提示词
        
        Args:
            session: 会话配置
            default_system_prompt: 默认系统提示词
        
        Returns:
            完整的系统提示词
        """
        logger.info(f"build_system_prompt - 传入的default_system_prompt: {default_system_prompt}")
        logger.info(f"build_system_prompt - session.get('custom_prompt'): {session.get('custom_prompt')}")
        
        if not session.get('custom_prompt', False):
            logger.info(f"build_system_prompt - 返回默认提示词: {default_system_prompt}")
            return default_system_prompt
        
        prompt_settings = session.get('prompt_settings', {})
        prompt_parts = [default_system_prompt]
        
        identity = prompt_settings.get('对方身份', '').strip()
        if identity:
            prompt_parts.append(f"对方身份：{identity}")
        
        tone = prompt_settings.get('语气态度', '').strip()
        if tone:
            prompt_parts.append(f"语气态度：{tone}")
        
        other = prompt_settings.get('其他', '').strip()
        if other:
            prompt_parts.append(f"其他：{other}")
        
        return "\n".join(prompt_parts)
    
    def generate_reply(self, formatted_messages: List[Dict], system_prompt: str, 
                       thinking_mode: bool = False, temperature: float = 1.3) -> Optional[str]:
        """
        使用 DeepSeek API 生成回复
        
        Args:
            formatted_messages: 格式化后的消息列表
            system_prompt: 系统提示词
            thinking_mode: 是否使用思考模式
            temperature: 温度参数
        
        Returns:
            生成的回复内容，失败返回 None
        """
        logger.info("开始生成 AI 回复...")
        logger.info(f"系统提示词: {system_prompt}")
        logger.info(f"格式化消息数量: {len(formatted_messages)}")
        
        deepseek_messages = [
            {"role": "system", "content": system_prompt},
            *formatted_messages
        ]
        
        try:
            is_reasoner = "reasoner" in self.model.lower()
            
            extra_body = {}
            if thinking_mode and not is_reasoner:
                extra_body = {"thinking": {"type": "enabled"}}
            
            request_params = {
                "model": self.model,
                "messages": deepseek_messages,
                "stream": False,
                "extra_body": extra_body
            }
            
            if not is_reasoner:
                request_params["temperature"] = temperature
            
            response = self.client.chat.completions.create(**request_params)
            
            if response and response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                reply = message.content
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    logger.info(f"AI 推理内容: {message.reasoning_content[:200]}...")
                logger.info(f"AI 回复生成成功: {reply}")
                return reply
            
            return None
        except Exception as e:
            logger.error(f"生成 AI 回复失败: {str(e)}")
            return None
    
    def generate_reply_stream(self, formatted_messages: List[Dict], system_prompt: str,
                              on_thinking_chunk: Optional[Callable[[str], None]] = None,
                              on_content_chunk: Optional[Callable[[str], None]] = None,
                              on_reasoning_finished: Optional[Callable[[], None]] = None,
                              thinking_mode: bool = False, temperature: float = 1.3) -> Optional[str]:
        """
        使用 DeepSeek API 流式生成回复
        
        Args:
            formatted_messages: 格式化后的消息列表
            system_prompt: 系统提示词
            on_thinking_chunk: 推理内容流式回调函数
            on_content_chunk: 最终内容流式回调函数
            on_reasoning_finished: 推理完成回调函数
            thinking_mode: 是否使用思考模式（对于 deepseek-reasoner 模型自动启用）
            temperature: 温度参数
        
        Returns:
            生成的完整回复内容，失败返回 None
        """
        logger.info("开始流式生成 AI 回复...")
        logger.info(f"系统提示词: {system_prompt}")
        logger.info(f"格式化消息数量: {len(formatted_messages)}")
        
        deepseek_messages = [
            {"role": "system", "content": system_prompt},
            *formatted_messages
        ]
        
        full_thinking = ""
        full_content = ""
        reasoning_started = False
        
        try:
            is_reasoner = "reasoner" in self.model.lower()
            
            extra_body = {}
            if thinking_mode and not is_reasoner:
                extra_body = {"thinking": {"type": "enabled"}}
            
            request_params = {
                "model": self.model,
                "messages": deepseek_messages,
                "stream": True,
                "extra_body": extra_body
            }
            
            if not is_reasoner:
                request_params["temperature"] = temperature
            
            response = self.client.chat.completions.create(**request_params)
            
            for chunk in response:
                delta = chunk.choices[0].delta
                
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    thinking_text = delta.reasoning_content
                    full_thinking += thinking_text
                    reasoning_started = True
                    if on_thinking_chunk:
                        on_thinking_chunk(thinking_text)
                
                if hasattr(delta, 'content') and delta.content:
                    if reasoning_started and on_reasoning_finished:
                        on_reasoning_finished()
                        reasoning_started = False
                    
                    content_text = delta.content
                    full_content += content_text
                    if on_content_chunk:
                        on_content_chunk(content_text)
            
            logger.info(f"AI 流式回复生成完成，最终内容长度: {len(full_content)}")
            if full_thinking:
                logger.info(f"推理内容长度: {len(full_thinking)}")
            
            return full_content if full_content else None
            
        except Exception as e:
            logger.error(f"流式生成 AI 回复失败: {str(e)}")
            return None
    
    def get_reply_for_session(self, weflow_base_url: str, session: Dict, 
                              default_system_prompt: str = "你模拟我与对方聊天。",
                              message_limit: int = 10, thinking_mode: bool = False,
                              temperature: float = 1.3) -> Optional[str]:
        """
        获取指定会话的 AI 回复（一站式方法）
        
        Args:
            weflow_base_url: WeFlow API 基础 URL
            session: 会话配置
            default_system_prompt: 默认系统提示词
            message_limit: 获取历史消息数量
            thinking_mode: 是否使用思考模式
            temperature: 温度参数
        
        Returns:
            生成的回复内容，失败返回 None
        """
        talker = session.get('wechat_id', '')
        if not talker:
            logger.error("会话 ID 为空，无法获取回复")
            return None
        
        messages = self.get_recent_messages(weflow_base_url, talker, message_limit)
        if not messages:
            logger.error("未获取到历史消息，无法生成回复")
            return None
        
        formatted_messages = self.format_messages_for_deepseek(messages, talker)
        system_prompt = self.build_system_prompt(session, default_system_prompt)
        
        return self.generate_reply(formatted_messages, system_prompt, thinking_mode, temperature)
    
    def get_reply_for_session_stream(self, weflow_base_url: str, session: Dict,
                                      on_thinking_chunk: Optional[Callable[[str], None]] = None,
                                      on_content_chunk: Optional[Callable[[str], None]] = None,
                                      on_reasoning_finished: Optional[Callable[[], None]] = None,
                                      default_system_prompt: str = "你模拟我与对方聊天。",
                                      message_limit: int = 10, thinking_mode: bool = False,
                                      temperature: float = 1.3) -> Optional[str]:
        """
        流式获取指定会话的 AI 回复（一站式方法）
        
        Args:
            weflow_base_url: WeFlow API 基础 URL
            session: 会话配置
            on_thinking_chunk: 推理内容流式回调函数
            on_content_chunk: 最终内容流式回调函数
            on_reasoning_finished: 推理完成回调函数
            default_system_prompt: 默认系统提示词
            message_limit: 获取历史消息数量
            thinking_mode: 是否使用思考模式
            temperature: 温度参数
        
        Returns:
            生成的完整回复内容，失败返回 None
        """
        talker = session.get('wechat_id', '')
        if not talker:
            logger.error("会话 ID 为空，无法获取回复")
            return None
        
        messages = self.get_recent_messages(weflow_base_url, talker, message_limit)
        if not messages:
            logger.error("未获取到历史消息，无法生成回复")
            return None
        
        formatted_messages = self.format_messages_for_deepseek(messages, talker)
        system_prompt = self.build_system_prompt(session, default_system_prompt)
        
        return self.generate_reply_stream(
            formatted_messages, system_prompt,
            on_thinking_chunk, on_content_chunk, on_reasoning_finished,
            thinking_mode, temperature
        )