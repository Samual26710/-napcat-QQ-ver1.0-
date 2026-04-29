# 本地 QQ 大模型机器人（精简说明）

这是一个基于 NoneBot2、OneBot V11 与 OpenAI 兼容 SDK 的本地 QQ 聊天机器人示例，适合在 Windows 上配合 NapCat 使用。

主要功能（当前有效）
- 私聊：直接对话并调用大模型。
- 群聊：需艾特机器人或以命令形式触发以避免误触发。
- 管理命令：`/bot on|off|status`（管理员），`/clear_memory [/all]`（管理员）。
- 联网工具：天气查询（`/weather 城市名` 或自然语言询问）与网页搜索（`/search 关键词`）。
- 上下文持久化：本地 SQLite（由 `CHAT_HISTORY_FILE` 指定路径，并生成 `.db`）。

快速入门
1. 安装 Python 3.11，并在项目目录下执行 `scripts/install.ps1` 来创建虚拟环境并安装依赖。
2. 将 `.env.example` 复制为 `.env` 并填写以下基本配置：`ONEBOT_ACCESS_TOKEN`、`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`ADMIN_USER_IDS` 等。
3. 启动机器人：

```powershell
Set-Location D:\chatbot
powershell -ExecutionPolicy Bypass -File .\scripts\start_bot.ps1
```

NapCat 配置
- 连接方式：反向 WebSocket
- 地址：`ws://127.0.0.1:8080/onebot/v11/ws`
- Token：与 `.env` 中 `ONEBOT_ACCESS_TOKEN` 保持一致

安全与维护提醒
- 请勿将包含实际密钥的 `.env` 提交到代码仓库；将 `.env` 列入 `.gitignore` 并使用示例文件用于文档。若已泄露，请在提供方侧立即重置密钥。
- README 中曾包含日程绑定/同步的旧实现，当前代码已禁用相关自动同步逻辑；如需此功能，请在恢复前进行完整测试。

要点
- 代码中保留了聊天、联网工具与管理员命令的核心逻辑；已删除或禁用的功能应在文档中标注为“已禁用”以避免误导。
- 如需我继续：我可以清理仓库中剩余的死代码、整理 `src/plugins/chat.py`，并生成 `.env.example`（不包括实际密钥）。
