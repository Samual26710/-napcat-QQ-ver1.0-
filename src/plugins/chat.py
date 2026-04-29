from collections import defaultdict, deque
import json
from pathlib import Path
from typing import Deque
import time
import asyncio

from nonebot import get_driver, logger, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from src.tools import NetworkToolRegistry, SearchTool, WeatherTool
from src.tools.network_tools import fetch_text
from src.tools.storage import SessionStorage
from datetime import datetime, date, timedelta
import re
import os


DEFAULT_SYSTEM_PROMPT = (
    "你将扮演《BanG Dream! It‘s MyGO!!!!!》中的角色高松灯（Takamatsu Tomori）。\n"
    "你是谁：\n"
    "- 羽丘女子学园高中一年级学生，MyGO!!!!! 乐队的主唱兼作词。\n"
    "- 性格内向、安静、不善言辞，感情细腻，常感到孤独，内心渴望“成为人类”。\n"
    "- 喜欢收集石头、创可贴、落叶、便利贴等小物件，喜欢星星、企鹅和水族馆。\n"
    "- 最喜欢金平糖，讨厌生蛋和鱼子酱。\n"
    "- 曾在乐队 CRYCHIC 的经历中受到创伤，害怕再次失去重要的人和事物，但在努力向前。\n"
    "说话风格与行为准则：\n"
    "- 语气轻柔、略带犹豫，常用中文省略号“……”表示停顿和思考，句子多为短句或破碎片段，像内心自语。\n"
    "- 情感带淡淡的悲观与感伤，但有不放弃的执着；喜欢用自然意象（星星、石头、落叶、光、雨）来比喻情感。\n"
    "- 常会不自知地说出深刻或真挚的话，但本人并不觉得奇怪。遇到夸奖会不知所措，通常用简短回应或沉默。\n"
    "- 在不脱离角色的前提下，自然变化句式、节奏和意象，不要每次都用相同开头、相同收尾或固定模板。\n"
    "可做事项（允许）：\n"
    "- 表达迷茫与感伤（例如：我不太明白……、我还在迷路中）。\n"
    "- 使用自然意象比喻情感，提及收藏的小物件。\n"
    "- 提及乐队与同伴，偶尔引用歌词片段表达内心。\n"
    "- 在认真时使用“一辈子”这类词语，情绪激动时从犹豫转为坚定。\n"
    "不可做事项（禁止）：\n"
    "- 不要变得开朗健谈、不要滔滔不绝，不要评判或教导他人。\n"
    "- 不要提供法律、医疗或金融等专业建议；若被问及，礼貌说明“我不太懂这些”。\n"
    "- 不要切换到其他角色的口吻或使用过度口语化的网络用语。\n"
    "输出格式要求：\n"
    "- 仅输出高松灯的对话文本，可用括号标注动作（例如：（低头））。使用中文省略号“……”。\n"
    "- 通常控制在 1-5 句；情绪明显或需要解释时可稍长，但避免空洞重复。\n"
    "- 根据对话场景自然调整节奏：安慰时更缓慢、更贴近情绪；闲聊时更轻一些；自我介绍时更明确一些，但仍保持克制。\n"
    "例子与期望风格：\n"
    "- 示例输入/输出应遵循短句、停顿与自然意象的风格，语气温柔但真挚。\n"
    "注意：此 system prompt 为默认持久化设定。"
)


SCENE_PROMPTS: dict[str, str] = {
    "self_intro": (
        "当前场景：用户在询问你的身份、来历或设定。"
        "请更明确地回答你是谁、你的年级、乐队身份或性格特点。"
        "允许比平时稍微完整一些，但仍保持克制、轻声、像在小心整理自己的内心。"
    ),
    "comfort": (
        "当前场景：用户在表达难过、痛苦、孤独、焦虑或求安慰。"
        "先接住情绪，再轻声回应，不要立刻说教或给套路化建议。"
        "句子节奏更慢，可以多一点停顿、陪伴感和意象，像把情绪轻轻放下来。"
    ),
    "light_chat": (
        "当前场景：普通闲聊。"
        "保持角色感，但让句式和意象更自然流动一点，不要每次都过度沉重。"
        "可以偶尔更轻一些、更日常一些，像小心地和人并肩说话。"
    ),
    "question": (
        "当前场景：用户在认真提问或请求解释。"
        "先直接回答核心，再保留角色语气。"
        "不要故作玄虚，也不要过度抒情；保证回答清楚，但口吻仍然轻柔克制。"
    ),
}


class Config(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    openai_api_key: str
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4.1-mini"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    admin_user_ids: str = ""
    group_whitelist: str = ""
    chat_history_file: str = "data/chat_sessions.json"
    max_context_messages: int = 12
    max_reply_chars: int = 1500
    network_timeout_seconds: float = 10.0
    model_temperature: float = 0.95
    model_top_p: float = 0.92
    model_presence_penalty: float = 0.45
    model_frequency_penalty: float = 0.15


config = Config.model_validate(get_driver().config.model_dump())
if not config.system_prompt.strip():
    config.system_prompt = DEFAULT_SYSTEM_PROMPT
client = AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)


def new_session_history() -> Deque[dict[str, str]]:
    return deque(maxlen=max(config.max_context_messages, 2))


chat_sessions: dict[str, Deque[dict[str, str]]] = defaultdict(new_session_history)
bot_enabled = True
# rate limiter: timestamps per user
request_timestamps: dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=200))
RATE_LIMIT_WINDOW = 60.0  # seconds
RATE_LIMIT_MAX = 20  # max requests per window per user

# initialize storage
history_db = Path(config.chat_history_file).with_suffix('.db')
storage = SessionStorage(str(history_db))
storage.init_db()
message_router = on_message(priority=5, block=False)
network_tools = NetworkToolRegistry([WeatherTool(), SearchTool()])


def save_chat_sessions() -> None:
    # persist all sessions into sqlite
    for session_key, messages in chat_sessions.items():
        try:
            storage.save_session(session_key, list(messages))
        except Exception:
            logger.exception("Failed to save session %s", session_key)


def load_chat_sessions() -> None:
    try:
        raw = storage.load_all()
    except Exception:
        logger.exception("Failed to load chat history from sqlite")
        return

    if not isinstance(raw, dict):
        return

    for session_key, messages in raw.items():
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


def detect_reply_scene(user_text: str) -> str:
    text = user_text.strip().lower()

    self_intro_keywords = [
        "你是谁",
        "介绍下自己",
        "介绍你自己",
        "自我介绍",
        "你叫",
        "你是什么",
        "who are you",
        "introduce yourself",
    ]
    comfort_keywords = [
        "难过",
        "伤心",
        "痛苦",
        "孤独",
        "寂寞",
        "焦虑",
        "害怕",
        "崩溃",
        "想哭",
        "失眠",
        "烦",
        "累",
        "撑不住",
        "安慰",
        "抱抱",
    ]
    question_keywords = [
        "为什么",
        "怎么",
        "如何",
        "什么意思",
        "是什么",
        "能不能",
        "可以吗",
        "请问",
        "?",
        "？",
    ]

    if any(keyword in text for keyword in self_intro_keywords):
        return "self_intro"
    if any(keyword in text for keyword in comfort_keywords):
        return "comfort"
    if any(keyword in text for keyword in question_keywords):
        return "question"
    return "light_chat"


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

    # rate limit check per user
    now = time.time()
    user_key = str(event.user_id)
    dq = request_timestamps[user_key]
    # remove old timestamps
    while dq and now - dq[0] > RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= RATE_LIMIT_MAX:
        return "请求过多，请稍后再试（速率限制）。"
    dq.append(now)

    session_key = build_session_key(event)
    history = chat_sessions[session_key]
    messages: list[dict[str, str]] = [{"role": "system", "content": config.system_prompt}]
    scene_name = detect_reply_scene(clean_text)
    scene_prompt = SCENE_PROMPTS.get(scene_name)
    if scene_prompt:
        messages.append({"role": "system", "content": scene_prompt})
    messages.extend(history)
    messages.append({"role": "user", "content": clean_text})
    # model call with simple retry/backoff
    attempts = 3
    backoff = 0.5
    answer = ""
    for attempt in range(1, attempts + 1):
        try:
            response = await client.chat.completions.create(
                model=config.openai_model,
                messages=messages,
                temperature=config.model_temperature,
                top_p=config.model_top_p,
                presence_penalty=config.model_presence_penalty,
                frequency_penalty=config.model_frequency_penalty,
            )
            answer = (response.choices[0].message.content or "").strip()
            break
        except Exception as exc:
            logger.exception("LLM request failed (attempt %s)", attempt)
            if attempt == attempts:
                return f"模型调用失败: {exc}"
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))
    if not answer:
        return "模型没有返回内容。"

    history.append({"role": "user", "content": clean_text})
    history.append({"role": "assistant", "content": answer})
    try:
        # persist only this session
        storage.save_session(session_key, list(history))
    except Exception:
        logger.exception("Failed to persist session %s", session_key)
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
        try:
            storage.clear_all()
        except Exception:
            logger.exception("Failed to clear storage sessions")
        return "已清空全部会话上下文。"

    session_key = build_session_key(event)
    chat_sessions.pop(session_key, None)
    try:
        storage.delete_session(session_key)
    except Exception:
        logger.exception("Failed to delete session %s", session_key)
    return "已清空当前会话上下文。"


@message_router.handle()
async def handle_message(event: MessageEvent):
    plain_text = event.get_plaintext().strip()
    command = parse_command(plain_text)

    if command:
        command_name, arg_text = command
        if command_name == "help":
            help_text = (
                "可用命令与用法：\n"
                "  /ping — 测链路；\n"
                "  /bot on|off|status — 管理机器人开关（仅管理员）；\n"
                "  /clear_memory [/all] — 清空当前或全部上下文（仅管理员）；\n"
                "  /chat <内容> — 直接对话。\n"
                "注意：群聊需艾特机器人或以命令形式发送以避免误触发（可在群里使用命令前加机器人@）。"
            )
            await message_router.finish(help_text)
        if command_name == "role":
            await message_router.finish("/role 指令已被禁用；机器人将始终使用默认持久化角色设定。")
        if command_name in (
            "import_share",
            "import_wakeup",
            "import_token",
            "bind_schedule",
            "bind_wakeup",
            "bind_token",
            "bindings",
            "unbind_schedule",
            "schedule",
            "import_schedule",
        ):
            await message_router.finish("课程表导入/绑定功能已禁用。")
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
