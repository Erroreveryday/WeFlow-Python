import json
import os

def load_config(config_file='config.json'):
    """
    加载配置文件，如果不存在则创建默认配置
    """
    if not os.path.exists(config_file):
        print(f"配置文件 {config_file} 不存在，正在创建默认配置...")
        default_config = {
            "weflow_api_port": 5031
        }
        save_config(default_config, config_file)
        return default_config
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"配置文件 {config_file} 加载成功")
        return config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 加载失败时返回默认配置
        default_config = {
            "weflow_api_port": 5031
        }
        return default_config

def save_config(config, config_file='config.json'):
    """
    保存配置文件
    返回 (success, message)
    """
    # 验证端口号
    if 'weflow_api_port' in config:
        port = config['weflow_api_port']
        if not isinstance(port, int):
            return False, "端口号必须是整数"
        if port < 1024 or port > 65535:
            return False, "端口号必须在 1024-65535 之间"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置文件 {config_file} 保存成功")
        return True, "配置保存成功"
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False, f"保存配置文件失败: {str(e)}"