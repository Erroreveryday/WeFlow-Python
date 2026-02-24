# WeFlow-Python

本项目是基于 [WeFlow](https://github.com/hicccc77/WeFlow) 项目（作者 [hicccc77](https://github.com/hicccc77)）的 HTTP API 开发的独立程序，通过调用 WeFlow HTTP API 实现接收并处理指定会话的消息。

本项目当前适配的 WeFlow 版本为 [v2.1.4](https://github.com/hicccc77/WeFlow/tree/v2.1.4)，使用本项目需先安装并配置好 WeFlow。

## 主要功能

- 通过调用 WeFlow HTTP API 实现实时接收指定微信会话的消息

## 项目结构

```
WeFlow-Python/
├── docs/
│   ├── WeFlow-HTTP-API.md      # WeFlow HTTP API 文档
├── src/
│   ├── main.py                 # 主入口
│   ├── config.ini              # 配置文件
│   ├── requirements.txt        # 依赖包列表
│   └── weflow/                 # WeFlow 相关模块
│       ├── __init__.py
│       ├── api_client.py       # WeFlow API 调用模块
│       └── message_listener.py # 消息监听模块
├── .gitignore
├── README.md
└── LICENSE
```

## 快速开始

### 安装步骤

1. **克隆项目**
   ```bash
   # 从 Gitee 克隆项目
   git clone https://gitee.com/logicliu/WeFlow-Python.git
   # 或从 GitHub 克隆项目
   git clone https://github.com/Erroreveryday/WeFlow-Python.git

   # 切换到项目目录
   cd WeFlow-Python
   ```

2. **创建并激活 conda 环境（可选）**
   ```bash
   conda create -n WeFlow python=3.10
   conda activate WeFlow
   ```

3. **安装依赖**
   ```bash
   pip install -r src/requirements.txt
   ```

### 如何运行

1. **启动 WeFlow**
   - 确保 WeFlow 已安装并运行
   - 确认 WeFlow HTTP API 服务已启动（启用方式：设置 → API 服务 → 启动服务）

2. **配置项目**
   - 编辑 `src/config.ini` 文件，设置监听的会话 ID 和其他配置项

3. **运行项目**
   ```bash
   conda activate WeFlow
   python src/main.py
   ```

## 配置说明

在 `src/config.ini` 文件中可以配置以下参数：

- `base_url`: WeFlow HTTP API 地址
- `talker`: 要监听的会话 ID
- `polling_interval`: 轮询间隔（秒）
- `limit`: 每次轮询获取的消息数量
- `media`: **[未测试]** 是否开启媒体导出（0/1）
- `start_mode`: 开始时间配置模式（1/2）
    - `start_date`: 方式1：指定日期，格式 YYYYMMDD
    - `start_days`: 方式2：往前推天数
- `log_level`: 日志级别

## 项目计划

- [x] 实现接收指定会话的消息
- [ ] 实现消息处理逻辑
- [ ] 实现微信自动回复
- [ ] 实现处理多个对话的消息

## 许可证

本项目是 WeFlow 的独立衍生应用，基于 MIT 许可证开源，您可以在遵守许可证条款的前提下自由使用、修改和分发本项目的代码。

详细信息请参阅 [LICENSE](LICENSE) 文件。