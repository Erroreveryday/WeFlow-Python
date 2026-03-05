import requests
import logging
from datetime import datetime
from typing import List, Dict
import json
import os
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "http://127.0.0.1:5031"
DEEPSEEK_API_KEY = "sk-xxx" # DeepSeek API 密钥
SYS_PROMPT = "你模拟我与对方聊天。我是xxx，说话风格xxx" # 系统提示词

# 初始化OpenAI客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def get_sessions() -> List[Dict]:
    """获取WeFlow的会话列表"""
    logging.info("开始获取会话列表...")
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/sessions",
            timeout=10
        )
        
        logging.info(f"请求状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('sessions'):
                sessions = data['sessions']
                logging.info(f"成功获取 {len(sessions)} 个会话")
                return sessions
            else:
                logging.error(f"API 响应异常: {data}")
                return []
        else:
            logging.error(f"API 请求失败，状态码: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求异常: {str(e)}")
        return []

def get_recent_messages(talker: str, limit: int = 10) -> List[Dict]:
    """从WeFlow获取指定会话的最近消息"""
    logging.info(f"开始获取会话 {talker} 的最近 {limit} 条消息...")
    try:
        params = {
            'talker': talker,
            'limit': limit
        }
        
        response = requests.get(
            f"{BASE_URL}/api/v1/messages",
            params=params,
            timeout=10
        )
        
        logging.info(f"请求状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('messages'):
                messages = data['messages']
                # 按时间从早到晚排序
                messages.sort(key=lambda x: x.get('createTime', 0))
                logging.info(f"成功获取 {len(messages)} 条消息")
                # 调试：打印时间戳值
                if messages:
                    logging.info(f"第一条消息时间戳: {messages[0].get('createTime', 'N/A')}")
                    logging.info(f"最后一条消息时间戳: {messages[-1].get('createTime', 'N/A')}")
                return messages
            else:
                logging.error(f"API 响应异常: {data}")
                return []
        else:
            logging.error(f"API 请求失败，状态码: {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求异常: {str(e)}")
        return []

def format_messages_for_deepseek(messages: List[Dict], talker: str) -> List[Dict]:
    """格式化消息为DeepSeek API所需的格式"""
    formatted_messages = []
    
    for msg in messages:
        # 简化身份标识
        sender = msg.get('senderUsername', '')
        
        # 判断是否是自己发送的消息：如果发送者不是talker，则是自己
        is_self = sender != talker
        
        # 构建消息内容
        content = msg.get('content', '')
        if msg.get('mediaType'):
            # 媒体消息
            media_type = msg.get('mediaType')
            content = f"[{media_type.upper()}] {content}"
        
        # 构建DeepSeek消息格式 - 对方是user，我是assistant
        formatted_msg = {
            "role": "assistant" if is_self else "user",
            "content": content
        }
        
        formatted_messages.append(formatted_msg)
    
    return formatted_messages

def test_non_thinking_mode(messages: List[Dict]):
    """测试非思考模式对话（流式输出）"""
    logging.info("开始测试非思考模式对话...")
    
    # 构建消息，添加系统提示词
    deepseek_messages = [
        {"role": "system", "content": SYS_PROMPT},
        *messages
    ]
    
    print("\n=== 非思考模式对话（流式输出）===")
    print(f"系统提示词: {SYS_PROMPT}")
    print("\n对话历史:")
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    
    print("\n模型回复（流式输出）:")
    try:
        # 流式调用DeepSeek API
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=deepseek_messages,
            stream=True,
            temperature=1.3
        )
        
        # 处理流式响应
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                full_response += content
        
        print("\n")
        logging.info("非思考模式对话测试完成")
        return full_response
    except Exception as e:
        logging.error(f"非思考模式对话测试失败: {str(e)}")
        return None

def test_thinking_mode(messages: List[Dict]):
    """测试思考模式对话（流式输出）"""
    logging.info("开始测试思考模式对话...")
    
    # 构建消息，添加系统提示词
    deepseek_messages = [
        {"role": "system", "content": SYS_PROMPT},
        *messages
    ]
    
    print("\n=== 思考模式对话（流式输出）===")
    print(f"系统提示词: {SYS_PROMPT}")
    print("\n对话历史:")
    for msg in messages:
        print(f"{msg['role']}: {msg['content']}")
    
    print("\n模型回复（流式输出，包含思考过程）:")
    try:
        # 流式调用DeepSeek API，开启思考模式
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=deepseek_messages,
            stream=True,
            temperature=1.3,
            extra_body={"thinking": {"type": "enabled"}}
        )
        
        # 处理流式响应
        full_response = ""
        thinking_content = ""
        reply_started = False
        for chunk in response:
            if chunk.choices[0].delta.reasoning_content:
                # 思考内容
                thinking = chunk.choices[0].delta.reasoning_content
                if not thinking_content:
                    print("思考过程:", end=" ", flush=True)
                print(thinking, end="", flush=True)
                thinking_content += thinking
            elif chunk.choices[0].delta.content:
                # 实际回复内容
                content = chunk.choices[0].delta.content
                if thinking_content and not reply_started:
                    print("\n回复:", end=" ", flush=True)
                    reply_started = True
                print(content, end="", flush=True)
                full_response += content
        
        print("\n")
        logging.info("思考模式对话测试完成")
        return full_response
    except Exception as e:
        logging.error(f"思考模式对话测试失败: {str(e)}")
        return None

def test_weflow_to_deepseek(talker: str = "wxid_xxx"):
    """测试从WeFlow获取消息并格式化到DeepSeek"""
    # 获取最近10条消息
    messages = get_recent_messages(talker, 10)
    
    if not messages:
        logging.error("未获取到消息")
        return False
    
    # 格式化消息
    formatted_messages = format_messages_for_deepseek(messages, talker)
    
    # 输出结果
    print("\n=== 原始消息 ===")
    for msg in messages:
        create_time = msg.get('createTime', 0)
        # 检查时间戳是否合理
        try:
            # 判断是秒级还是毫秒级时间戳
            if create_time < 10000000000:  # 小于10位，秒级时间戳
                time_str = datetime.fromtimestamp(create_time).strftime('%Y-%m-%d %H:%M:%S')
            else:  # 大于等于10位，毫秒级时间戳
                time_str = datetime.fromtimestamp(create_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # 如果时间戳解析失败，使用当前时间
            time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{time_str}] {msg.get('senderUsername', '')}: {msg.get('content', '')}")
    
    print("\n=== 格式化后消息 ===")
    for msg in formatted_messages:
        print(f"{msg['role']}: {msg['content']}")
    
    # 测试非思考模式
    test_non_thinking_mode(formatted_messages)
    
    # 测试思考模式
    test_thinking_mode(formatted_messages)
    
    logging.info("测试完成")
    return True

if __name__ == "__main__":
    # 检查OpenAI SDK是否安装
    try:
        import openai
    except ImportError:
        print("请先安装OpenAI SDK: pip install openai")
        exit(1)
    
    # 获取会话列表
    sessions = get_sessions()
    
    if not sessions:
        print("未获取到会话列表，无法进行测试")
        exit(1)
    
    # 显示会话列表供用户选择
    print("\n=== 会话列表 ===")
    for i, session in enumerate(sessions[:10]):  # 只显示前10个会话
        username = session.get('username', '未知')
        display_name = session.get('displayName', '未知')
        last_message = session.get('lastMessage', '无')
        print(f"{i+1}. {display_name} ({username})")
        print(f"   最后一条消息: {last_message}")
    
    # 让用户选择一个会话
    try:
        choice = int(input("\n请选择要测试的会话编号 (1-10): "))
        if 1 <= choice <= min(10, len(sessions)):
            selected_session = sessions[choice-1]
            test_talker = selected_session.get('username')
            print(f"\n已选择会话: {selected_session.get('displayName')} ({test_talker})")
            
            # 测试消息获取和格式化
            success = test_weflow_to_deepseek(test_talker)
            if success:
                print("\n测试通过: 消息获取和格式化成功")
            else:
                print("\n测试失败: 消息获取或格式化失败")
        else:
            print("无效的选择")
    except ValueError:
        print("请输入有效的数字")