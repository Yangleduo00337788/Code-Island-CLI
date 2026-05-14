<div align="center">

# CodeIsland

![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![DeepSeek](https://img.shields.io/badge/DeepSeek-Supported-4F46E5?style=flat-square)
![OpenAI](https://img.shields.io/badge/OpenAI-Compatible-412991?style=flat-square&logo=openai)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

**一款开源的命令行 AI 编程助手，支持多提供商与自主工具调用，专为DeepSeek打造！！！**

[快速开始](#快速开始) | [命令行参考](#命令行参考) | [AI 工具系统](#ai-工具系统) | [配置指南](#配置指南) | [问题反馈](https://github.com/yourusername/aicli/issues)

</div>

---

## 项目简介

CodeIsland 是一个类 Claude Code / Cursor 终端版本的 AI 编程助手，**完全开源、本地可控**。AI 可以在对话中自主调用读写文件、搜索代码、执行命令等工具来完成编程任务，支持 DeepSeek、OpenAI、Claude、Moonshot、Ollama 等主流 AI 后端。

## 技术栈

### 运行时

| 技术 | 版本 | 说明 |
|------|------|------|
| Python | 3.9+ | 运行环境 |
| Click | 8.1+ | CLI 框架 |
| httpx | 0.25+ | 异步 HTTP 客户端 |
| Rich | 13.0+ | 终端渲染引擎 |
| prompt-toolkit | 3.0+ | 交互式输入组件 |

### 数据与验证

| 技术 | 版本 | 说明 |
|------|------|------|
| Pydantic | 2.0+ | 数据模型验证 |
| toml | 0.10+ | 配置文件解析 |
| Pygments | - | 语法高亮（可选） |

### 开发工具

| 技术 | 版本 | 说明 |
|------|------|------|
| pytest | 7.0+ | 测试框架 |
| pytest-asyncio | - | 异步测试支持 |
| ruff | 0.1+ | 代码风格检查 |
| mypy | 1.0+ | 静态类型检查 |

## 项目结构

```
aicli
├── src/aicli               # 核心代码
│   ├── __init__.py          # 版本声明
│   ├── cli.py               # CLI 入口（Chat/Ask/Config 等命令）
│   ├── config.py            # 三层配置管理（文件/环境变量/CLI）
│   ├── chat.py              # 交互式对话循环 + 工具调用循环
│   ├── tools.py             # 7 个系统工具定义与执行器
│   ├── tool_loop.py         # 旧版工具循环（兼容保留）
│   ├── history.py           # 会话历史管理（保存/加载/导出）
│   ├── ui.py                # 终端 UI 渲染（欢迎页/状态栏/流式输出）
│   ├── utils.py             # 文件读取/stdin 读取等工具函数
│   └── providers/           # AI 提供商适配层
│       ├── __init__.py      # 工厂模式创建提供商
│       ├── base.py          # BaseProvider 抽象基类
│       ├── openai_provider.py  # OpenAI 兼容（DeepSeek/Moonshot）
│       ├── claude_provider.py  # Anthropic Claude
│       └── ollama_provider.py  # Ollama 本地模型
│
├── tests/                   # 测试目录
│   ├── test_config.py       # 配置模块测试
│   └── test_providers.py    # 提供商模块测试
│
└── pyproject.toml           # 项目配置与依赖管理
```

## 功能特性

### 多提供商支持
- **DeepSeek** — 支持推理过程显示（reasoning_content），性价比高
- **OpenAI** — 广泛兼容，支持所有工具
- **Claude** — 强大的编程能力
- **Moonshot** — 国产大模型，长上下文支持
- **Ollama** — 本地运行，免费无需 API Key

### 交互式对话
- 持久会话，带历史上下文
- 流式输出 + Markdown 实时渲染
- 会话保存/加载/导出（JSON + Markdown）
- 内联命令 / 文件引用 / 输入历史

### AI 工具系统
- **read_file** — 读取文件（支持行号范围）
- **write_file** — 写入或创建文件
- **edit_file** — 精确查找替换编辑
- **execute_command** — 执行系统命令（需审批）
- **list_directory** — 列出目录内容
- **search_files** — Glob 搜索文件
- **search_content** — 正则搜索文件内容

### 灵活配置
- 配置文件 + 环境变量 + CLI 参数三层覆盖
- 支持图片验证码、滑块验证码、短信验证码
- RSA 非对称接口加密

### 会话管理
- 保存 / 加载 / 导出对话历史
- 撤销上一轮对话
- 重试上一次请求

## 快速开始

### 环境准备

- Python 3.9+

### 安装

```bash
git clone <仓库地址>
cd aicli

# 生产安装
pip install .

# 开发安装
pip install -e ".[dev]"
```

### 配置 API Key

```bash
# 交互式配置
aicli setup

# 直接指定
aicli setup --provider deepseek --api-key sk-xxx

# 使用环境变量
export DEEPSEEK_API_KEY=sk-xxx
```

### 启动对话

```bash
# 交互式聊天（推荐）
aicli chat

# Claude Code 风格（chat 别名）
aicli code

# 单次提问
aicli ask "Python 如何排序列表？"

# 带文件上下文
aicli ask "请审查这段代码" --file main.py

# 管道输入
cat app.py | aicli ask "这段代码有什么 bug？"
```

## 命令行参考

### `aicli chat` — 交互式对话

```bash
aicli chat                          # 默认配置启动
aicli chat -p openai -m gpt-4o      # 指定提供商和模型
aicli chat --system "你是Python专家"  # 自定义系统提示词
aicli chat --no-stream               # 禁用流式输出
```

### `aicli ask` — 单次提问

```bash
aicli ask "什么是闭包？"
aicli ask -p claude "解释这段代码" --file code.py
echo "def foo(): pass" | aicli ask "有改进空间吗？"
```

### `aicli models` — 查看模型

```bash
aicli models                # 查看当前提供商模型
aicli models -p openai      # 查看 OpenAI 模型
```

### `aicli setup` — 配置提供商

```bash
aicli setup                      # 交互式配置
aicli setup -p openai -k sk-xxx  # 直接指定
```

### `aicli config` — 查看配置

显示当前配置文件和运行时配置信息。

```bash
aicli config
```

### `aicli history` — 会话管理

```bash
aicli history list    # 列出所有已保存会话
```

### 内置命令

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助信息 |
| `/model` | 切换当前模型 |
| `/provider` | 切换提供商 |
| `/setup` | 重新配置 API Key |
| `/clear` | 清空对话历史 |
| `/config` | 显示当前配置 |
| `/save <名称>` | 保存会话 |
| `/load <名称>` | 加载会话 |
| `/export <名称>` | 导出会话（JSON + Markdown） |
| `/undo` | 撤销上一轮对话 |
| `/retry` | 重试上次请求 |
| `/exit` | 退出程序 |

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Alt+Enter` | 换行 |
| `Esc` | 中断 AI 响应 |
| `Ctrl+C` | 中断 / 退出（按两次） |
| `Ctrl+P` | 命令面板 |
| `↑` / `↓` | 浏览输入历史 |

## AI 工具系统

AI 可在对话中自主调用以下工具完成编程任务：

| 工具 | 说明 | 需审批 |
|------|------|--------|
| `read_file` | 读取文件内容（支持行号范围） | ❌ |
| `write_file` | 写入或创建文件 | ❌ |
| `edit_file` | 精确查找替换编辑 | ❌ |
| `execute_command` | 执行系统命令（编译/测试等） | ✅ |
| `list_directory` | 列出目录内容 | ❌ |
| `search_files` | Glob 搜索文件 | ❌ |
| `search_content` | 正则搜索文件内容 | ❌ |

> `execute_command` 默认需用户审批，保障安全。

### 工具调用流程

```
用户提问 → AI 思考 → 调用工具 → 显示结果 → AI 继续分析 → ... → 最终回答
```

## 配置指南

### 配置优先级

```
CLI 参数 > 环境变量 > 配置文件
```

### 配置文件位置

| 系统 | 路径 |
|------|------|
| Linux/macOS | `~/.config/aicli/config.toml` |
| Windows | `%APPDATA%/aicli/config.toml` |

### 配置文件示例

```toml
[default]
provider = "deepseek"
model = "deepseek-chat"
stream = true
history_size = 100

[providers.deepseek]
api_key = "sk-xxx"
base_url = "https://api.deepseek.com"

[providers.openai]
api_key = "sk-xxx"
base_url = "https://api.openai.com"

[providers.claude]
api_key = "sk-ant-xxx"
base_url = "https://api.anthropic.com"

[providers.moonshot]
api_key = "sk-xxx"
base_url = "https://api.moonshot.cn"

[providers.ollama]
base_url = "http://localhost:11434"
```

### 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `AICLI_PROVIDER` | 默认提供商 | `deepseek` |
| `AICLI_MODEL` | 默认模型 | `deepseek-chat` |
| `AICLI_STREAM` | 流式输出开关 | `true` |
| `DEEPSEEK_API_KEY` | DeepSeek Key | `sk-xxx` |
| `OPENAI_API_KEY` | OpenAI Key | `sk-xxx` |
| `ANTHROPIC_API_KEY` | Claude Key | `sk-ant-xxx` |

### 支持的提供商

| 提供商 | 默认模型 | 特性 |
|--------|---------|------|
| **DeepSeek** | `deepseek-chat` | 推理过程显示，性价比高 |
| **OpenAI** | `gpt-4o` | 最广泛兼容 |
| **Claude** | `claude-3-5-sonnet-20241022` | 强大编程能力 |
| **Moonshot** | `moonshot-v1-8k` | 长上下文 |
| **Ollama** | `llama3` | 本地免费运行 |

## 开发指南

### 添加新提供商

在 `src/aicli/providers/` 下创建新适配器，继承 `BaseProvider` 实现 `chat` 和 `get_available_models` 方法，然后在工厂函数中注册：

```python
# providers/__init__.py
def create_provider(provider_name, api_key, base_url):
    if provider_name == "newprovider":
        return NewProvider(api_key=api_key, base_url=base_url)
```

### 添加新工具

在 `src/aicli/tools.py` 中添加工具定义和执行函数，AI 即可在后续对话中自动使用。

### 运行测试

```bash
pytest
```

### 代码检查

```bash
ruff check .
mypy src/
```

## 更新日志

### v0.1.0
- 搭建项目基础框架
- 支持 DeepSeek / OpenAI / Claude / Moonshot / Ollama 多提供商
- 实现交互式对话与流式输出
- 实现 AI 自主工具调用（7 个系统工具）
- 支持会话保存/加载/导出
- 三层配置管理（文件/环境变量/CLI）
- 精美终端 UI（Rich 渲染 + Catppuccin 配色）

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 开源协议

本项目基于 [MIT License](LICENSE) 开源。

## 致谢

- [Click](https://click.palletsprojects.com/) — CLI 框架
- [Rich](https://rich.readthedocs.io/) — 终端渲染
- [httpx](https://www.python-httpx.org/) — 异步 HTTP 客户端
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) — 交互式输入
- [Pydantic](https://docs.pydantic.dev/) — 数据验证

---

<div align="center">

**如果这个项目对你有帮助，请给一个 Star 支持一下！**

</div>
