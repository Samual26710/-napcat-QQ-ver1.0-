# 本地 QQ 大模型机器人

这是一个基于 NoneBot2、OneBot V11 和 OpenAI Python SDK 的本地 QQ 聊天机器人最小可运行项目，适合在 Windows 上配合 NapCat 使用。

## 技术选型

- Python 框架: NoneBot2
- QQ 协议接入: NapCatQQ
- 适配器: nonebot-adapter-onebot
- 大模型 SDK: OpenAI Python SDK

## 目录结构

```text
.
|-- bot.py
|-- requirements.txt
|-- start_bot_all.bat
|-- stop_bot_all.bat
|-- .env.example
|-- src/
|   |-- tools/
|   |   |-- __init__.py
|   |   `-- network_tools.py
|   `-- plugins/
|       |-- __init__.py
|       `-- chat.py
`-- scripts/
    |-- check_status.ps1
    |-- install.ps1
    |-- install_autostart.ps1
    |-- remove_autostart.ps1
    |-- start_all.ps1
    |-- start_bot.ps1
    `-- stop_all.ps1
```

## 1. 准备环境

- Windows 10 或 11
- Python 3.11，并确保 `python` 或 `py` 已加入 PATH
- 已安装并可登录的 QQ NT 客户端
- NapCatQQ

## 2. 安装依赖

在 PowerShell 中执行:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1
```

执行后会自动:

- 创建 `.venv`
- 安装依赖
- 复制 `.env.example` 为 `.env`

## 3. 填写配置

编辑 `.env`:

```env
HOST=127.0.0.1
PORT=8080
ONEBOT_ACCESS_TOKEN=自行生成一个随机 token
OPENAI_API_KEY=你的模型平台密钥
OPENAI_BASE_URL=模型平台的 OpenAI 兼容地址
OPENAI_MODEL=模型名
SYSTEM_PROMPT=你是一个简洁、可靠、遵守指令的 QQ 助手。
ADMIN_USER_IDS=管理员QQ号,多个用英文逗号分隔
GROUP_WHITELIST=
CHAT_HISTORY_FILE=data/chat_sessions.json
MAX_CONTEXT_MESSAGES=12
MAX_REPLY_CHARS=1500
NETWORK_TIMEOUT_SECONDS=10
```

说明:

- `OPENAI_BASE_URL` 可以替换成任何兼容 OpenAI 接口的平台地址。
- `ADMIN_USER_IDS` 用于指定可执行管理员命令的 QQ 号，多个用英文逗号分隔。
- `GROUP_WHITELIST` 留空表示所有群都可用；填群号时用英文逗号分隔。
- `CHAT_HISTORY_FILE` 用于指定上下文持久化文件路径，默认保存在 `data/chat_sessions.json`。
- `NETWORK_TIMEOUT_SECONDS` 用于控制联网查询超时时间，默认 10 秒。
- 私聊支持直接自然语言对话。
- 群聊需要艾特机器人后再发送内容，避免误触发。
- `/ping`、`/bot`、`/clear_memory`、`/chat` 会按收到的原始文本直接解析，减少不同 QQ 客户端下的命令匹配差异。
- 已加入独立联网工具层，当前已接入天气查询和网页搜索，后续可继续扩展新闻、汇率等外部能力。
- 当前天气工具可用 `/weather 城市名` 或直接问“北京天气怎么样”。
- 当前搜索工具可用 `/search 关键词`，或直接说“搜索 量子计算最新进展”。

## 4. 启动机器人

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\start_bot.ps1
```

默认监听:

- HTTP: `127.0.0.1:8080`
- OneBot 反向 WebSocket 路径: `/onebot/v11/ws`

## 5. 配置 NapCat

在 NapCat 中启用 OneBot V11，并配置:

- 连接方式: 反向 WebSocket
- 地址: `ws://127.0.0.1:8080/onebot/v11/ws`
- Token: 与 `.env` 中 `ONEBOT_ACCESS_TOKEN` 一致

配置完成后，让 NapCat 发起连接。

## 6. 验证

先验证链路:

```text
/ping
```

说明:

- 私聊里可直接发送 `/ping`。
- 群聊里建议直接发送 `/ping` 测链路；自然语言对话则仍建议先艾特机器人。

如果返回 `pong`，说明 QQ、NapCat 和 NoneBot 已经打通。

再验证大模型:

私聊机器人时，可直接发送:

```text
你好，请做个自我介绍
```

群聊中，需要先艾特机器人，再发送内容，例如:

```text
@机器人 你好，请做个自我介绍
```

如果返回模型内容，说明整条链路和模型调用都已打通。

验证联网天气:

```text
/weather 北京
```

或直接发送:

```text
北京天气怎么样
```

如果返回实时天气，说明联网查询能力已经可用。

验证联网搜索:

```text
/search Python 3.13 新特性
```

或直接发送:

```text
搜索 Python 3.13 新特性
```

如果返回搜索结果列表和链接，说明联网搜索能力已经可用。

管理员命令:

```text
/bot status
/bot on
/bot off
/clear_memory
/clear_memory all
```

说明:

- `/bot on|off|status` 仅管理员可用，用于控制机器人全局开关。
- `/clear_memory` 清空当前会话上下文，并同步更新本地持久化文件。
- `/clear_memory all` 清空全部会话上下文，并同步更新本地持久化文件。
- 机器人关闭后，私聊直聊、群聊艾特触发和 `/chat` 都会停止回复，但 `/ping` 仍可用于检查链路。

## 7. 上线建议

本地长期运行建议默认使用手动一键启动，而不是开机自启:

1. QQ 设置自动登录。
2. NapCat 放在固定目录，例如 `D:\NapCat`。
3. 需要使用时，再手动启动 NapCat 和机器人。

手动同时启动 NapCat 和机器人:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\start_all.ps1
```

也可以直接双击项目根目录下的启动文件，这是当前推荐方式:

```text
start_bot_all.bat
```

停止 NapCat 和机器人:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\stop_all.ps1
```

也可以直接双击项目根目录下的停止文件:

```text
stop_bot_all.bat
```

如果你之前开启过开机自启，可执行以下命令移除:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\remove_autostart.ps1
```

如需重新安装开机自启，也仍可手动执行:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\install_autostart.ps1
```

检查当前本地状态:

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\check_status.ps1
```

这个脚本会检查:

- bot 进程是否存在
- NapCat 进程是否存在
- 系统版 QQ 是否仍在运行
- 8080 端口是否在监听
- NapCat 与 bot 是否已经建立连接
- 上下文持久化文件是否存在

说明:

- 当前推荐使用手动一键启动，不依赖 Windows 开机自启。
- 开机自启使用 Windows 启动文件夹快捷方式，只对当前登录用户生效。
- `start_bot.ps1` 和 `start_napcat.ps1` 都带有“已运行则不重复启动”的保护。
- `start_napcat.ps1` 默认使用机器人 QQ 号 `3882941016` 进行快速登录，避免每次都扫码。
- 如果你修改了 `.env`，仍然需要重启机器人进程后才会生效。

NapCat 登录说明:

- 第一次登录或登录态失效时，NapCat 仍然可能要求扫码。
- 如果 QQ 登录态仍然有效，之后通过 `start_napcat.ps1`、`start_all.ps1` 或开机自启启动时，通常不需要重复扫码。
- 如果你想强制使用扫码登录，可手动运行 `D:\NapCat\napcat.bat`。

## 8. 当前能力

- 私聊直接对话
- 私聊 `/ping`
- 私聊 `/weather 城市名`
- 私聊 `/search 关键词`
- 私聊管理员命令 `/bot` 和 `/clear_memory`
- 群聊艾特触发对话
- 群聊 `/ping`
- 群聊 `/weather 城市名`
- 群聊 `/search 关键词`
- 群聊管理员命令 `/bot` 和 `/clear_memory`
- 群白名单控制
- 管理员全局开关
- 管理员清空上下文
- 基于本地 JSON 持久化的短上下文
- 基于联网接口的实时天气查询
- 基于联网接口的网页搜索结果查询

## 9. 后续增强

- 改成艾特触发
- 上下文持久化到本地文件或数据库
- 增加管理员命令
- 增加敏感词和速率限制
- 增加日志轮转和异常重连
