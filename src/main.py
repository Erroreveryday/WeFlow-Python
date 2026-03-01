#!/usr/bin/env python3
from gui.main_window import main
from utils import load_config

if __name__ == "__main__":
    # 加载配置文件，不存在则自动创建
    config = load_config()
    main()