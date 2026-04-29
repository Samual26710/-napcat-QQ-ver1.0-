import re
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote
from xml.etree import ElementTree as ET

import httpx
import asyncio
from nonebot import logger


@dataclass(frozen=True)
class ToolMatch:
    tool_name: str
    query: str
    source: str


class NetworkTool(Protocol):
    name: str

    def match_command(self, command_name: str, arg_text: str) -> ToolMatch | None:
        ...

    def match_natural_language(self, text: str) -> ToolMatch | None:
        ...

    async def execute(self, query: str, timeout_seconds: float) -> str:
        ...


async def fetch_json(url: str, params: dict[str, str], timeout_seconds: float) -> dict:
    timeout = httpx.Timeout(timeout_seconds)
    attempts = 3
    backoff = 0.5
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client_http:
                response = await client_http.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            last_exc = exc
            logger.warning("fetch_json attempt %s failed for %s: %s", attempt, url, exc)
            if attempt == attempts:
                raise
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))


async def fetch_text(url: str, params: dict[str, str], timeout_seconds: float) -> str:
    timeout = httpx.Timeout(timeout_seconds)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    }
    attempts = 3
    backoff = 0.5
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client_http:
                response = await client_http.get(url, params=params)
                response.raise_for_status()
                return response.text
        except Exception as exc:
            logger.warning("fetch_text attempt %s failed for %s: %s", attempt, url, exc)
            if attempt == attempts:
                raise
            await asyncio.sleep(backoff * (2 ** (attempt - 1)))


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class WeatherTool:
    name = "weather"
    command_names = {"weather", "天气"}
    natural_patterns = [
        re.compile(r"^(?:查询|看看|看下|帮我查|帮我看看)(?P<location>.+?)天气(?:怎么样|如何|咋样|呢|预报)?$"),
        re.compile(r"^(?P<location>.+?)天气(?:怎么样|如何|咋样|呢|预报)?$"),
        re.compile(r"^(?P<location>.+?)(?:今天天气|实时天气|天气预报)$"),
        re.compile(r"^(?P<location>.+?)(?:温度|气温)(?:多少|怎么样)?$"),
    ]

    def match_command(self, command_name: str, arg_text: str) -> ToolMatch | None:
        if command_name not in self.command_names:
            return None
        query = arg_text.strip()
        if not query:
            return ToolMatch(tool_name=self.name, query="", source="command")
        return ToolMatch(tool_name=self.name, query=query, source="command")

    def match_natural_language(self, text: str) -> ToolMatch | None:
        clean_text = text.strip()
        if not clean_text:
            return None

        for pattern in self.natural_patterns:
            match = pattern.match(clean_text)
            if not match:
                continue

            location = match.group("location").strip(" ，。?？")
            if location:
                return ToolMatch(tool_name=self.name, query=location, source="natural")

        return None

    async def execute(self, query: str, timeout_seconds: float) -> str:
        location = query.strip()
        if not location:
            return "用法: /weather 北京"

        encoded_location = quote(location)
        try:
            weather_data = await fetch_json(
                f"https://wttr.in/{encoded_location}",
                {"format": "j1"},
                timeout_seconds,
            )
        except Exception as exc:
            logger.exception("Weather request failed")
            return f"天气查询失败，联网请求出错: {exc}"

        nearest_area = weather_data.get("nearest_area") or []
        current_list = weather_data.get("current_condition") or []
        if not nearest_area or not current_list:
            return f"没有找到“{location}”对应的天气地点，请换个更具体的城市名。"

        area = nearest_area[0]
        current = current_list[0]
        city_name = ((area.get("areaName") or [{}])[0]).get("value") or location
        region_name = ((area.get("region") or [{}])[0]).get("value") or ""
        country_name = ((area.get("country") or [{}])[0]).get("value") or ""
        weather_desc = ((current.get("weatherDesc") or [{}])[0]).get("value") or "未知天气"
        region = " ".join(part for part in [country_name, region_name, city_name] if part)

        return (
            f"{region} 当前天气:\n"
            f"天气: {weather_desc}\n"
            f"气温: {current.get('temp_C', '--')}°C\n"
            f"体感: {current.get('FeelsLikeC', '--')}°C\n"
            f"湿度: {current.get('humidity', '--')}%\n"
            f"风速: {current.get('windspeedKmph', '--')} km/h"
        )


class SearchTool:
    name = "search"
    command_names = {"search", "搜索"}
    natural_patterns = [
        re.compile(r"^(?:搜索|搜一下|帮我搜|帮我搜索)(?P<query>.+)$"),
        re.compile(r"^(?:查询|查一下|帮我查)(?P<query>.+?)(?:资料|信息|内容)?$"),
    ]
    max_results = 5

    def match_command(self, command_name: str, arg_text: str) -> ToolMatch | None:
        if command_name not in self.command_names:
            return None
        query = arg_text.strip()
        return ToolMatch(tool_name=self.name, query=query, source="command")

    def match_natural_language(self, text: str) -> ToolMatch | None:
        clean_text = text.strip()
        if not clean_text:
            return None

        for pattern in self.natural_patterns:
            match = pattern.match(clean_text)
            if not match:
                continue

            query = match.group("query").strip(" ，。?？")
            if query and not query.endswith("天气"):
                return ToolMatch(tool_name=self.name, query=query, source="natural")

        return None

    async def execute(self, query: str, timeout_seconds: float) -> str:
        clean_query = query.strip()
        if not clean_query:
            return "用法: /search 关键词"

        try:
            rss_text = await fetch_text(
                "https://cn.bing.com/search",
                {"q": clean_query, "format": "rss"},
                timeout_seconds,
            )
        except Exception as exc:
            logger.exception("Search request failed")
            return f"搜索失败，联网请求出错: {exc}"

        try:
            root = ET.fromstring(rss_text)
        except Exception as exc:
            logger.exception("Search RSS parse failed")
            return f"搜索失败，解析搜索结果时出错: {exc}"

        items = root.findall("./channel/item")
        if not items:
            return f"没有找到与“{clean_query}”相关的网页结果。"

        lines = [f"搜索结果: {clean_query}"]
        for index, item in enumerate(items[: self.max_results], start=1):
            title = normalize_whitespace(item.findtext("title") or "无标题")
            url = normalize_whitespace(item.findtext("link") or "")
            snippet = normalize_whitespace(item.findtext("description") or "")

            lines.append(f"{index}. {title}")
            if snippet:
                lines.append(f"   摘要: {snippet[:120]}")
            lines.append(f"   链接: {url}")

        lines.append("可继续发送 /search 关键词，或让我基于其中某条结果继续总结。")
        return "\n".join(lines)


class NetworkToolRegistry:
    def __init__(self, tools: list[NetworkTool]):
        self.tools = tools

    def match_command(self, command_name: str, arg_text: str) -> ToolMatch | None:
        for tool in self.tools:
            match = tool.match_command(command_name, arg_text)
            if match:
                return match
        return None

    def match_natural_language(self, text: str) -> ToolMatch | None:
        for tool in self.tools:
            match = tool.match_natural_language(text)
            if match:
                return match
        return None

    async def execute(self, match: ToolMatch, timeout_seconds: float) -> str:
        for tool in self.tools:
            if tool.name == match.tool_name:
                return await tool.execute(match.query, timeout_seconds)
        return "未找到对应的联网工具。"