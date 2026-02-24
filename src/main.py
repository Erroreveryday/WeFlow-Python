import configparser
import logging
import time
from weflow.api_client import WeFlowAPIClient
from weflow.message_listener import MessageListener
from weflow.aliyun_ai import AliyunAIClient

def setup_logging(log_level):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """主函数"""
    # 读取配置文件
    import os
    config = configparser.ConfigParser()
    config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_file_path, encoding='utf-8')
    
    # 获取配置项
    base_url = config.get('WeFlow', 'base_url')
    talker = config.get('WeFlow', 'talker')
    polling_interval = config.getint('WeFlow', 'polling_interval')
    limit = config.getint('WeFlow', 'limit')
    log_level = config.get('WeFlow', 'log_level')
    
    # 开始时间配置
    start_mode = config.getint('WeFlow', 'start_mode', fallback=2)
    start_date = config.get('WeFlow', 'start_date', fallback=None)
    start_days = config.getint('WeFlow', 'start_days', fallback=7)
    
    # 阿里云AI配置
    aliyun_api_key = config.get('AliyunAI', 'api_key')
    aliyun_model = config.get('AliyunAI', 'model', fallback='qwen-flash')
    history_count = config.getint('AliyunAI', 'history_count', fallback=20)
    
    # 根据 start_mode 决定使用哪种方式
    if start_mode == 1:
        # 方式1：使用指定日期
        start_days = None
    elif start_mode == 2:
        # 方式2：使用往前推天数
        start_date = None
    
    # 设置日志
    setup_logging(log_level)
    logger = logging.getLogger(__name__)
    
    logger.info("开始启动 WeFlow 消息监听服务")
    
    # 创建 API 客户端
    api_client = WeFlowAPIClient(base_url)
    
    # 健康检查
    logger.info("正在进行健康检查...")
    health_status = api_client.health_check()
    if health_status:
        logger.info("健康检查成功: %s", health_status)
    else:
        logger.error("健康检查失败，请确保 WeFlow API 服务已启动")
        return
    
    # 创建阿里云AI客户端
    aliyun_ai_client = AliyunAIClient(api_key=aliyun_api_key, model=aliyun_model)
    
    # 创建消息监听器
    listener = MessageListener(
        api_client=api_client,
        talker=talker,
        polling_interval=polling_interval,
        limit=limit,
        start_date=start_date,
        start_days=start_days,
        aliyun_ai_client=aliyun_ai_client,
        history_count=history_count
    )
    
    # 启动监听器
    listener.start()
    
    try:
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在停止服务...")
    finally:
        # 停止监听器
        listener.stop()
        logger.info("WeFlow 消息监听服务已停止")

if __name__ == "__main__":
    main()
