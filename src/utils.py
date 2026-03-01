import json
import os

def load_config(config_file='config.json'):
    """
    加载配置文件，如果不存在则创建默认配置
    """
    if not os.path.exists(config_file):
        print(f"配置文件 {config_file} 不存在，正在创建默认配置...")
        default_config = {
            "weflow_api_port": 5031,
            "weflow_api": {
                "limit": 3
            },
            "wechat_sessions": [
                {
                    "wechat_id": "",
                    "contact_remark": "",
                    "auto_reply": False,
                    "custom_prompt": False, 
                    "prompt_settings": {
                        "对方身份": "",
                        "语气态度": "",
                        "其他": ""
                    }
                }
            ],
            "wechat_shortcuts": {
                "show_hide_window": "Ctrl+Alt+W",
                "send_message": "Enter"
            },
            "ai": {
                "provider": "aliyun",
                "model": "qwen3.5-flash",
                "api_key": "",
                "providers": {
                    "aliyun": {
                        "models": ["qwen3.5-flash", "qwen3.5-plus", "qwen3-max"]
                    },
                    "deepseek": {
                        "models": ["deepseek-chat", "deepseek-reasoner"]
                    }
                }
            }
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
            "weflow_api_port": 5031,
            "weflow_api": {
                "limit": 3
            },
            "wechat_sessions": [
                {
                    "wechat_id": "",
                    "contact_remark": "",
                    "auto_reply": False,
                    "custom_prompt": False, 
                    "prompt_settings": {
                        "对方身份": "",
                        "语气态度": "",
                        "其他": ""
                    }
                }
            ],
            "wechat_shortcuts": {
                "show_hide_window": "Ctrl+Alt+W",
                "send_message": "Enter"
            },
            "ai": {
                "provider": "aliyun",
                "model": "qwen3.5-flash",
                "api_key": "",
                "providers": {
                    "aliyun": {
                        "models": ["qwen3.5-flash", "qwen3.5-plus", "qwen3-max"]
                    },
                    "deepseek": {
                        "models": ["deepseek-chat", "deepseek-reasoner"]
                    }
                }
            }
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
    
    # 验证 AI 配置
    if 'ai' in config:
        ai_config = config['ai']
        if 'provider' in ai_config:
            provider = ai_config['provider']
            valid_providers = ['aliyun', 'deepseek']
            if provider not in valid_providers:
                return False, f"AI 服务商必须是 {valid_providers} 之一"
            
            if 'model' in ai_config:
                model = ai_config['model']
                if 'providers' in ai_config and provider in ai_config['providers']:
                    valid_models = ai_config['providers'][provider].get('models', [])
                    if model not in valid_models:
                        return False, f"AI 模型必须是 {valid_models} 之一"
            else:
                return False, "必须指定 AI 模型"
            
            # API 密钥可以为空，由用户自行配置
            if 'api_key' in ai_config and not isinstance(ai_config['api_key'], str):
                return False, "API 密钥必须是字符串"
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置文件 {config_file} 保存成功")
        return True, "配置保存成功"
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False, f"保存配置文件失败: {str(e)}"