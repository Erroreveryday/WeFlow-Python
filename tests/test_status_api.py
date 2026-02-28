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

if __name__ == "__main__":
    success = test_api_health()
    if success:
        print("测试通过: API 服务运行正常")
    else:
        print("测试失败: API 服务异常")
