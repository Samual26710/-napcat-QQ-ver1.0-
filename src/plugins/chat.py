from collections import defaultdict, deque
import json
from pathlib import Path
from typing import Deque

from nonebot import get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from src.tools import NetworkToolRegistry, SearchTool, WeatherTool


class Config(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    system_prompt: str = "你是一个简洁、可靠、遵守指令的 QQ 助手。"
    admin_user_ids: str = ""
    group_whitelist: str = ""
    chat_history_file: str = "data/chat_sessions.json"
    max_context_messages: int = 12
    max_reply_chars: int = 1500
    network_timeout_seconds: float = 10.0


config = Config.model_validate(get_driver().config.model_dump())
client = AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)


def new_session_history() -> Deque[dict[str, str]]:
    return deque(maxlen=max(config.max_context_messages, 2))


chat_sessions: dict[str, Deque[dict[str, str]]] = defaultdict(new_session_history)
bot_enabled = True
message_router = on_message(priority=5, block=False)
network_tools = NetworkToolRegistry([WeatherTool(), SearchTool()])


def save_chat_sessions() -> None:
    history_path = Path(config.chat_history_file)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    serializable = {session_key: list(messages) for session_key, messages in chat_sessions.items()}
    history_path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_chat_sessions() -> None:
    history_path = Path(config.chat_history_file)
    if not history_path.exists():
        return

    try:
        raw_data = json.loads(history_path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to load chat history")
        return

    if not isinstance(raw_data, dict):
        logger.warning("Chat history file format is invalid")
        return

    for session_key, messages in raw_data.items():
        if not isinstance(session_key, str) or not isinstance(messages, list):
            continue

        history = new_session_history()
        for message in messages:
            if not isinstance(message, dict):
                continue
            role = message.get("role")
            content = message.get("content")
            if isinstance(role, str) and isinstance(content, str):
                history.append({"role": role, "content": content})

        if history:
            chat_sessions[session_key] = history


load_chat_sessions()


def build_session_key(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f"group:{event.group_id}:user:{event.user_id}"
    return f"private:{event.user_id}"


def is_group_allowed(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return True
    if not config.group_whitelist.strip():
        return True
    allowed = {item.strip() for item in config.group_whitelist.split(",") if item.strip()}
    return str(event.group_id) in allowed


def is_admin(event: MessageEvent) -> bool:
    if not config.admin_user_ids.strip():
        return False
    admin_ids = {item.strip() for item in config.admin_user_ids.split(",") if item.strip()}
    return str(event.user_id) in admin_ids


def is_group_chat_triggered(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return True
    return bool(getattr(event, "to_me", False))


def parse_command(text: str) -> tuple[str, str] | None:
    clean_text = text.strip()
    if not clean_text.startswith("/"):
        return None

    body = clean_text[1:].strip()
    if not body:
        return "", ""

    command, _, arg = body.partition(" ")
    return command.lower(), arg.strip()


async def build_chat_reply(event: MessageEvent, user_text: str) -> str:
    if not is_group_allowed(event):
        return "当前群未加入白名单。"
    if not bot_enabled:
        return "机器人当前已关闭，请联系管理员开启。"

    clean_text = user_text.strip()
    if not clean_text:
        if isinstance(event, GroupMessageEvent):
            return "请在艾特机器人后输入要说的话。"
        return "请直接发送你想说的话。"

    session_key = build_session_key(event)
    history = chat_sessions[session_key]
    messages: list[dict[str, str]] = [{"role": "system", "content": config.system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": clean_text})

    try:
        response = await client.chat.completions.create(
            model=config.openai_model,
            messages=messages,
            temperature=0.7,
        )
    except Exception as exc:
        logger.exception("LLM request failed")
        return f"模型调用失败: {exc}"

    answer = (response.choices[0].message.content or "").strip()
    if not answer:
        return "模型没有返回内容。"

    history.append({"role": "user", "content": clean_text})
    history.append({"role": "assistant", "content": answer})
    save_chat_sessions()
    return answer[: config.max_reply_chars]


async def handle_ping(event: MessageEvent) -> str:
    if not is_group_allowed(event):
        return "当前群未加入白名单。"
    return "pong"


async def handle_bot_command(event: MessageEvent, arg_text: str) -> str:
    global bot_enabled

    if not is_admin(event):
        return "你不是管理员，无法执行该命令。"

    action = arg_text.strip().lower()
    if not action:
        status_text = "开启" if bot_enabled else "关闭"
        return f"当前机器人状态: {status_text}\n用法: /bot on|off|status"

    if action == "on":
        bot_enabled = True
        return "机器人已开启。"
    if action == "off":
        bot_enabled = False
        return "机器人已关闭。"
    if action == "status":
        status_text = "开启" if bot_enabled else "关闭"
        return f"当前机器人状态: {status_text}"

    return "用法: /bot on|off|status"


async def handle_clear_memory(event: MessageEvent, arg_text: str) -> str:
    if not is_admin(event):
        return "你不是管理员，无法执行该命令。"

    action = arg_text.strip().lower()
    if action == "all":
        chat_sessions.clear()
        save_chat_sessions()
        return "已清空全部会话上下文。"

    session_key = build_session_key(event)
    chat_sessions.pop(session_key, None)
    save_chat_sessions()
    return "已清空当前会话上下文。"
@message_router.handle()
async def handle_message(event: MessageEvent):
    plain_text = event.get_plaintext().strip()
    command = parse_command(plain_text)

    if command:
        command_name, arg_text = command
        tool_match = network_tools.match_command(command_name, arg_text)
        if tool_match:
            logger.info("Network tool matched: tool=%s source=%s query=%s", tool_match.tool_name, tool_match.source, tool_match.query)
            await message_router.finish(await network_tools.execute(tool_match, config.network_timeout_seconds))

        if command_name == "ping":
            await message_router.finish(await handle_ping(event))
        if command_name == "bot":
            await message_router.finish(await handle_bot_command(event, arg_text))
        if command_name == "clear_memory":
            await message_router.finish(await handle_clear_memory(event, arg_text))
        if command_name == "chat":
            if not arg_text:
                await message_router.finish("用法: /chat 你好")
            await message_router.finish(await build_chat_reply(event, arg_text))

    if isinstance(event, GroupMessageEvent) and not is_group_chat_triggered(event):
        return

    if not plain_text:
        if isinstance(event, GroupMessageEvent):
            await message_router.finish("请在艾特机器人后输入要说的话。")
        return

    logger.info(
        "Incoming message routed: user_id=%s group_id=%s to_me=%s text=%s",
        event.user_id,
        getattr(event, "group_id", "private"),
        getattr(event, "to_me", False),
        plain_text,
    )

    tool_match = network_tools.match_natural_language(plain_text)
    if tool_match:
        logger.info("Network tool matched: tool=%s source=%s query=%s", tool_match.tool_name, tool_match.source, tool_match.query)
        await message_router.finish(await network_tools.execute(tool_match, config.network_timeout_seconds))

    await message_router.finish(await build_chat_reply(event, plain_text))
