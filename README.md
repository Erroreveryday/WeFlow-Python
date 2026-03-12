# WeFlow-Python

> 警告：近期存在大规模封号，使用 WeFlow 可能会导致微信账号异常

本项目是基于 [WeFlow](https://github.com/hicccc77/WeFlow) 项目（作者 [hicccc77](https://github.com/hicccc77)）的 HTTP API 开发的独立程序，通过调用 WeFlow HTTP API 实现接收并处理指定会话的消息。

本项目当前适配的 WeFlow 版本为 [v2.4.0](https://github.com/hicccc77/WeFlow/tree/v2.4.0)，使用本项目需先安装并配置好 WeFlow。项目开发所用的微信版本为 [4.1.7.30](https://weixin.qq.com/updates?platform=windows&version=4.1.7)。

## 主要功能

- 通过调用 WeFlow HTTP API 实现实时接收指定微信会话的消息
- 处理消息并调用 DeepSeek 大模型生成回复内容
- 通过模拟快捷键操作微信，实现自动回复消息

## 项目结构

```
WeFlow-Python/
├── docs/                          # 项目文档目录
│   ├── DeepSeek-API.md            # DeepSeek API 文档
│   └── WeFlow-HTTP-API.md         # WeFlow HTTP API 文档
├── src/                           # 项目源代码目录
│   ├── main.py                    # 主入口
│   ├── gui/                       # GUI 模块
│   │   └── main_window.py         # 主窗口
│   ├── utils/                     # 工具模块
│   │   ├── __init__.py            # 初始化模块
│   │   ├── config.py              # 配置管理
│   │   └── deepseek.py            # DeepSeek AI 调用模块
│   └── weflow/                    # WeFlow 相关模块
│       ├── __init__.py            # 初始化模块
│       ├── keyboard_automation.py # 键盘操作模块
│       ├── message_listener.py    # WeFlow 消息监听模块
│       └── status_checker.py      # 状态检查模块
├── tests/                         # 测试目录
│   ├── test_api_keyword_filter.py
│   ├── test_status_api.py
│   ├── test_status_weixin.py
│   └── test_weflow_messages_to_deepseek.py
├── .gitignore                     # Git 忽略文件
├── README.md                      # 项目说明文档
├── LICENSE                        # 开源许可证
└── requirements.txt               # 依赖包列表
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
   conda create -n your_env python=3.10
   conda activate your_env
   ```

3. **安装依赖**
   ```bash
   pip install -r src/requirements.txt
   ```

### 如何运行

1. **前置条件**
   - 确保 WeFlow 已安装并运行，且 HTTP API 服务已启动（启用方式：设置 → API 服务 → 启动服务）

2. **运行项目**
   ```bash
   conda activate your_env # 激活 conda 环境（如果使用）
   python src/main.py
   ```

### 注意事项

- 确保 WeFlow HTTP API 服务已启动
- 微信需保持登录状态，否则无法监听消息
- 程序执行操作时，请不要手动操作微信窗口，否则可能会导致程序异常或错误

## 配置说明

### 微信会话配置

- 可添加 / 删除会话，`微信ID` 和 `联系人备注` 为必填项
- 微信 ID 可在 WeFlow `聊天` 的 `会话详情` 中查看 **（暂不支持群聊）**
- 当前仅支持同时监听一个会话

### 微信快捷键配置

- 需与微信端的快捷键配置一致，否则无法正常工作
- 微信快捷键设置入口：`微信` → `设置` → `快捷键`

### WeFlow API 配置

- 需与 WeFlow 配置一致，否则无法正常工作
- WeFlow 配置入口：`WeFlow` → `设置` → `API服务`

### 自动回复配置

- 有 **回复固定文本** 和 **调用AI大模型** 两种自动回复模式
- **回复固定文本**：用户可以预设固定文本，当收到消息时直接回复该文本
- **调用AI大模型**：用户可以配置 DeepSeek 大模型 API 密钥，当收到消息时调用模型生成回复内容
   - 密钥：可在 DeepSeek 官网注册获取：[DeepSeek 开放平台](https://platform.deepseek.com/)
   - 模型：支持思考模式和非思考模式两种模型
   - 系统提示词：自定义模型在生成回复前的提示词，用于引导模型生成符合要求的回复内容

## 项目计划

- [ ] 实现调用阿里云 AI 模型生成回复消息
- [ ] 实现手动回复，用户可以在没有新消息时手动触发回复
- [ ] 实现 AI 模式下自定义历史消息的发送数量
- [ ] 实现中止生成回复的功能
- [ ] 实现同时处理多个会话

## 隐私声明

- 本项目不会以任何方式收集用户的隐私信息，包括但不限于：微信聊天记录、WeFlow 数据库密钥、AI 大模型 API 密钥、AI 大模型生成的回复内容等
- AI 大模型服务直接与模型供应商进行通信，没有经过任何服务器中转

## 许可证

本项目是 WeFlow 的独立衍生应用，基于 GPL v2 许可证开源，您可以在遵守许可证条款的前提下自由使用、修改和分发本项目的代码。

详细信息请参阅 [LICENSE](LICENSE) 文件。