# aicli 🚀

> **AI CLI** — 一个强大的命令行 AI 编程助手，支持多提供商，具备自主工具调用能力的智能终端工具。

类似于 Claude Code / Cursor 的终端版本，但**完全开源、本地可控**，支持多种 AI 后端。

---

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🤖 **多提供商支持** | DeepSeek / OpenAI / Claude / Moonshot / Ollama（本地模型） |
| 🛠️ **自主工具调用** | AI 可自主读写文件、搜索代码、执行命令来完成编程任务 |
| 💬 **交互式对话** | 带历史记录、流式输出、Markdown 实时渲染 |
| 📁 **文件感知** | 使用 `@文件名` 或 `/file <路径>` 引用文件 |
| 🎨 **精美终端 UI** | Rich 渲染、状态指示、动画效果、语法高亮 |
| ⚙️ **灵活配置** | 配置文件 + 环境变量 + CLI 参数，三层覆盖优先级 |
| 📝 **会话管理** | 保存 / 加载 / 导出对话历史（JSON + Markdown） |
| 🔄 **管道支持** | 支持标准输入管道，方便集成到工作流 |
| 🧠 **思考过程** | 支持显示 DeepSeek 等模型的推理过程（reasoning_content） |

---

## 📦 安装

### 从源码安装

```bash
git clone <仓库地址>
cd aicli
pip install .
```

### 开发模式安装

```bash
pip install -e ".[dev]"
```

---

## ⚡ 快速开始

### 1. 配置 API Key

```bash
# 交互式配置
aicli setup

# 或直接指定
aicli setup --provider deepseek --api-key sk-xxx

# 或使用环境变量
export DEEPSEEK_API_KEY=sk-xxx
```

### 2. 开始对话

```bash
# 交互式聊天（推荐）
aicli chat

# Claude Code 风格（别名）
aicli code

# 单次提问
aicli ask "Python 如何排序列表？"

# 带文件上下文
aicli ask "请审查这段代码" --file main.py

# 管道输入
cat app.py | aicli ask "这段代码有什么 bug？"
```

---

## 📖 命令行参考

### `aicli chat` — 交互式对话

启动一个持久的交互式对话会话，AI 可以自主调用工具完成任务。

```bash
aicli chat                          # 使用默认配置
aicli chat -p openai -m gpt-4o      # 指定提供商和模型
aicli chat --system "你是Python专家"  # 自定义系统提示词
aicli chat --no-stream              # 禁用流式输出
aicli chat --approve                # 自动批准工具操作
```

### `aicli code` — Claude Code 风格对话

`chat` 命令的别名，提供相同的交互体验。

### `aicli ask` — 单次提问

提出单个问题，完成后退出。

```bash
aicli ask "什么是闭包？"
aicli ask -p claude "解释这段代码" --file code.py
echo "def foo(): pass" | aicli ask "有改进空间吗？"
```

### `aicli models` — 查看可用模型

```bash
aicli models                    # 查看当前提供商模型
aicli models -p openai          # 查看 OpenAI 模型
aicli models -p deepseek        # 查看 DeepSeek 模型
```

### `aicli setup` — 配置提供商

交互式配置 API Key、Base URL 和默认模型。

```bash
aicli setup                      # 交互式配置
aicli setup -p openai -k sk-xxx  # 直接配置
```

### `aicli config` — 查看配置

显示当前配置文件和运行时的配置信息。

```bash
aicli config
```

### `aicli history` — 会话管理

```bash
aicli history list    # 列出所有已保存的会话
```

---

## 🎮 交互式聊天功能

### 内置命令

在对话中输入以下命令控制会话：

| 命令 | 功能 |
|------|------|
| `/help` | 显示帮助信息 |
| `/model` | 显示并切换当前模型 |
| `/model <名称>` | 直接切换到指定模型 |
| `/provider` | 切换 AI 提供商 |
| `/setup` | 重新配置 API Key |
| `/clear` | 清除当前对话历史 |
| `/config` | 显示当前配置 |
| `/save <名称>` | 保存当前会话 |
| `/load <名称>` | 加载已保存的会话 |
| `/export <名称>` | 将会话导出为 JSON + Markdown |
| `/undo` | 撤销上一轮对话 |
| `/retry` | 重试上一次请求 |
| `/exit` | 退出程序 |

### 文件引用

- **`@文件名`** — 在消息中引用文件内容
- **`/file <路径>`** — 专门分析某个文件

### 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Alt+Enter` | 换行（多行输入） |
| `Esc` | 中断当前 AI 响应 |
| `Ctrl+C` | 中断 / 退出（按两次） |
| `Ctrl+P` | 打开命令面板 |
| `↑` / `↓` | 浏览输入历史 |

---

## 🛠️ AI 工具系统

AI 可以在对话中自主调用以下工具来完成编程任务：

| 工具 | 说明 | 需要审批 |
|------|------|---------|
| `read_file` | 读取文件内容（支持行号和行数限制） | ❌ |
| `write_file` | 写入或创建文件 | ❌ |
| `edit_file` | 精确查找替换编辑文件 | ❌ |
| `execute_command` | 执行系统命令（如编译、测试） | ✅ |
| `list_directory` | 列出目录内容 | ❌ |
| `search_files` | 使用 glob 模式搜索文件 | ❌ |
| `search_content` | 使用正则表达式搜索文件内容 | ❌ |

> **安全机制**：`execute_command` 默认需要用户审批，可通过 `--approve` 标志自动批准。

### 工具调用流程

```
用户提问 → AI 思考 → 调用工具 → 显示结果 → AI 继续 → ... → 最终回答
```

工具调用会以清晰的分隔线展示，并显示每个工具的执行结果（或截断预览）。

---

## ⚙️ 配置

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
auto_approve = false

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
| `AICLI_STREAM` | 是否启用流式输出 | `true` |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | `sk-xxx` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-xxx` |
| `ANTHROPIC_API_KEY` | Claude API Key | `sk-ant-xxx` |

---

## 🔌 支持的提供商

| 提供商 | 默认模型 | 特性 |
|--------|---------|------|
| **DeepSeek** | `deepseek-chat` | 支持推理过程显示，性价比高 |
| **OpenAI** | `gpt-4o` | 最广泛兼容，支持所有工具 |
| **Claude** | `claude-3-5-sonnet-20241022` | 强大的编程能力 |
| **Moonshot** | `moonshot-v1-8k` | 国产大模型，长上下文 |
| **Ollama** | `llama3` | 本地运行，免费，无需 API Key |

> 所有与 OpenAI API 兼容的服务（如 vLLM、Together AI、Groq 等）也可通过配置 Base URL 使用。

---

## 🧪 开发

### 环境准备

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码检查

```bash
ruff check .          # 代码风格检查
mypy src/             # 类型检查
```

### 项目结构

```
src/aicli/
├── __init__.py          # 版本信息
├── cli.py               # CLI 入口（Click 命令组）
├── config.py            # 配置管理（文件 + 环境变量 + CLI 参数）
├── chat.py              # 核心对话逻辑 + 工具循环
├── tools.py             # 7 个系统工具的定义和执行器
├── tool_loop.py         # 旧的工具循环（已弃用，保留兼容）
├── history.py           # 会话历史管理
├── ui.py                # 终端 UI 渲染
├── utils.py             # 通用工具函数
└── providers/           # AI 提供商适配器
    ├── __init__.py      # 工厂函数
    ├── base.py          # 抽象基类
    ├── openai_provider.py  # OpenAI 兼容（DeepSeek/OpenAI/Moonshot）
    ├── claude_provider.py  # Anthropic Claude
    └── ollama_provider.py  # Ollama 本地模型
```

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- [Click](https://click.palletsprojects.com/) — CLI 框架
- [Rich](https://rich.readthedocs.io/) — 终端渲染
- [httpx](https://www.python-httpx.org/) — 异步 HTTP 客户端
- [prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/) — 交互式输入
- [Pydantic](https://docs.pydantic.dev/) — 数据验证
