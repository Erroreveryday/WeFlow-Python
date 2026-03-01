import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "http://127.0.0.1:5031"

def test_api_health():
    """测试 API 健康状态"""
    logging.info("开始测试 API 健康状态...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        logging.info(f"请求状态码: {response.status_code}")
        logging.info(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "ok":
                logging.info("API 服务运行正常")
                return True
            else:
                logging.error(f"API 响应状态异常: {data}")
                return False
        else:
            logging.error(f"API 请求失败，状态码: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"API 请求异常: {str(e)}")
        return False

def get_test_talker():
    """获取一个测试用的会话 ID"""
    logging.info("开始获取测试会话...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/sessions", params={"limit": 5}, timeout=10)
        logging.info(f"获取会话列表状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and data.get("sessions"):
                sessions = data.get("sessions")
                logging.info(f"获取到 {len(sessions)} 个会话")
                for session in sessions:
                    talker = session.get("username")
                    display_name = session.get("displayName")
                    logging.info(f"会话: {display_name} (ID: {talker})")
                return sessions[0].get("username") if sessions else None
            else:
                logging.error(f"获取会话列表失败: {data}")
                return None
        else:
            logging.error(f"获取会话列表请求失败，状态码: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"获取会话列表异常: {str(e)}")
        return None

def test_keyword_filter(talker, keyword):
    """测试关键词过滤功能"""
    logging.info(f"开始测试关键词过滤功能，talker: {talker}, keyword: {keyword}")
    try:
        # 先获取原始消息（不带关键词过滤）
        response1 = requests.get(f"{BASE_URL}/api/v1/messages", 
                               params={"talker": talker, "limit": 50}, 
                               timeout=10)
        logging.info(f"获取原始消息状态码: {response1.status_code}")
        
        if response1.status_code != 200:
            logging.error(f"获取原始消息失败，状态码: {response1.status_code}")
            return False
        
        data1 = response1.json()
        total_messages = len(data1.get("messages", []))
        logging.info(f"原始消息数量: {total_messages}")
        
        # 再获取带关键词过滤的消息
        response2 = requests.get(f"{BASE_URL}/api/v1/messages", 
                               params={"talker": talker, "limit": 50, "keyword": keyword}, 
                               timeout=10)
        logging.info(f"获取过滤消息状态码: {response2.status_code}")
        
        if response2.status_code != 200:
            logging.error(f"获取过滤消息失败，状态码: {response2.status_code}")
            return False
        
        data2 = response2.json()
        filtered_messages = len(data2.get("messages", []))
        logging.info(f"过滤后消息数量: {filtered_messages}")
        
        # 验证过滤效果
        if filtered_messages <= total_messages:
            logging.info(f"关键词过滤有效: 从 {total_messages} 条消息中过滤出 {filtered_messages} 条")
            
            # 打印过滤后的消息内容
            if filtered_messages > 0:
                logging.info("过滤后的消息示例:")
                for msg in data2.get("messages", [])[:5]:  # 只显示前5条
                    content = msg.get("content", "")
                    sender = msg.get("senderUsername", "")
                    create_time = msg.get("createTime", 0)
                    logging.info(f"[{sender}] {content} (时间: {create_time})")
            return True
        else:
            logging.error(f"关键词过滤无效: 过滤后消息数({filtered_messages})大于原始消息数({total_messages})")
            return False
            
    except requests.exceptions.RequestException as e:
        logging.error(f"测试关键词过滤异常: {str(e)}")
        return False

if __name__ == "__main__":
    # 1. 测试 API 健康状态
    health_ok = test_api_health()
    if not health_ok:
        print("测试失败: API 服务异常")
        exit(1)
    
    # 2. 获取测试会话
    talker = get_test_talker()
    if not talker:
        print("测试失败: 无法获取测试会话")
        exit(1)
    
    # 3. 测试关键词过滤
    # 请根据实际情况修改关键词
    test_keywords = ["你好", "好的", "工作", "学习"]
    
    for keyword in test_keywords:
        print(f"\n=== 测试关键词: {keyword} ===")
        success = test_keyword_filter(talker, keyword)
        if success:
            print(f"测试通过: 关键词 '{keyword}' 过滤功能正常")
        else:
            print(f"测试失败: 关键词 '{keyword}' 过滤功能异常")
    
    print("\n测试完成")