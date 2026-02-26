import configparser
import logging
import time
import sys

def setup_logging(log_level):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    """主函数"""
    listener = None
    logger = None
    
    try:
        # 首先设置基本日志，确保即使在配置文件读取失败时也能记录错误
        setup_logging('INFO')
        logger = logging.getLogger(__name__)
        
        # 读取配置文件
        import os
        config = configparser.ConfigParser()
        
        # 处理打包后的路径问题
        if hasattr(sys, '_MEIPASS'):
            # 打包后环境
            config_file_path = os.path.join(sys._MEIPASS, 'config.ini')
        else:
            # 开发环境
            config_file_path = os.path.join(os.path.dirname(__file__), 'config.ini')
        
        logger.info(f"尝试读取配置文件: {config_file_path}")
        config.read(config_file_path, encoding='utf-8')
        
        # 获取配置项
        base_url = config.get('WeFlow', 'base_url')
        talker = config.get('WeFlow', 'talker')
        polling_interval = config.getint('WeFlow', 'polling_interval')
        limit = config.getint('WeFlow', 'limit')
        log_level = config.get('WeFlow', 'log_level')
        
        # 重新设置日志级别
        setup_logging(log_level)
        logger = logging.getLogger(__name__)
        
        # 开始时间配置
        start_mode = config.getint('WeFlow', 'start_mode', fallback=2)
        start_date = config.get('WeFlow', 'start_date', fallback=None)
        start_days = config.getint('WeFlow', 'start_days', fallback=7)
        
        # 阿里云AI配置
        aliyun_api_key = config.get('AliyunAI', 'api_key')
        aliyun_model = config.get('AliyunAI', 'model', fallback='qwen-flash')
        history_count = config.getint('AliyunAI', 'history_count', fallback=20)
        
        # 微信配置
        target_session = config.get('WeChat', 'target_session', fallback='文件传输助手')
        
        # 根据 start_mode 决定使用哪种方式
        if start_mode == 1:
            # 方式1：使用指定日期
            start_days = None
        elif start_mode == 2:
            # 方式2：使用往前推天数
            start_date = None
        
        logger.info("开始启动 WeFlow 消息监听服务")
        
        # 动态导入模块，这样可以捕获导入错误
        from weflow.api_client import WeFlowAPIClient
        from weflow.message_listener import MessageListener
        from weflow.aliyun_ai import AliyunAIClient
        
        # 创建 API 客户端
        api_client = WeFlowAPIClient(base_url)
        
        # 健康检查
        logger.info("正在进行健康检查...")
        health_status = api_client.health_check()
        if health_status:
            logger.info("健康检查成功: %s", health_status)
        else:
            logger.error("健康检查失败，请确保 WeFlow API 服务已启动")
            # 不直接返回，而是继续执行，等待用户手动退出
        
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
            history_count=history_count,
            config=config,
            target_session=target_session
        )
        
        # 启动监听器
        listener.start()
        
        # 保持程序运行
        logger.info("服务已启动，按回车键或 Ctrl+C 退出...")
        input()
    except Exception as e:
        # 确保即使logger未初始化也能显示错误信息
        if logger:
            logger.error(f"发生错误: {str(e)}")
            logger.info("程序遇到错误，按回车键或 Ctrl+C 退出...")
        else:
            print(f"发生错误: {str(e)}")
            print("程序遇到错误，按回车键或 Ctrl+C 退出...")
        input()
    finally:
        # 停止监听器
        if listener:
            if logger:
                logger.info("正在停止 WeFlow 消息监听服务...")
            listener.stop()
            if logger:
                logger.info("WeFlow 消息监听服务已停止")
        if logger:
            logger.info("程序已退出")
        else:
            print("程序已退出")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"发生错误: {str(e)}")
        print("程序遇到错误，按回车键或 Ctrl+C 退出...")
        input()