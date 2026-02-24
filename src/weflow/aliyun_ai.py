import os
import logging
from dashscope import Generation
import dashscope

class AliyunAIClient:
    def __init__(self, api_key, model="qwen-flash"):
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        # 设置API地址
        dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    
    def generate_reply(self, messages):
        """调用阿里云AI生成回复"""
        try:
            response = Generation.call(
                api_key=self.api_key,
                model=self.model,
                messages=messages,
                result_format="message",
                enable_thinking=False,  # 不开启深度思考
            )
            
            if response.status_code == 200:
                # 返回生成的回复
                return response.output.choices[0].message.content
            else:
                self.logger.error(f"AI生成回复失败: HTTP返回码：{response.status_code}, 错误码：{response.code}, 错误信息：{response.message}")
                return None
        except Exception as e:
            self.logger.error(f"调用阿里云AI时出错: {e}")
            return None