from typing import Any, Union, Callable, Optional, cast, Type, ClassVar
from pydantic import BaseModel, Field, ValidationError
from typing_extensions import override
from pathlib import Path
from yarl import URL
import contextlib
import asyncio
import random
import hashlib
import time
import secrets
import json
import sys
import base64
import re

from nonebot import get_plugin_config
from nonebot.utils import logger_wrapper
from nonebot.exception import WebSocketClosed
from nonebot.utils import DataclassEncoder, escape_tag
from nonebot.drivers import (
    URL,
    Driver,
    Request,
    Response,
    ASGIMixin,
    WebSocket,
    WebSocketClientMixin,
    ForwardDriver,
    ReverseDriver,
    HTTPClientMixin,
    HTTPServerSetup,
    WebSocketServerSetup,
)
from nonebot.adapters import Adapter as BaseAdapter

from .bot import Bot
from .event import *
from .utils import log, escape, unescape
from .config import Config, BotInfo
from .exception import (
    ActionFailed,
    NetworkError,
    ApiNotAvailable,
    UnkonwnEventError,
)


class Adapter(BaseAdapter):
    @override
    def __init__(self, driver: Driver, **kwargs: Any):
        super().__init__(driver, **kwargs)
        self.cx_config: Config = get_plugin_config(Config)

        self.connections: dict[str, WebSocket] = {}
        self.tasks: set[asyncio.Task] = set()

        self.setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        """适配器名称: `ChaoXing`"""
        return "ChaoXing"

    def setup(self) -> None:
        if not isinstance(self.driver, WebSocketClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} "
                "doesn't support websocket client connections!"
                f"{self.get_name()} Adapter needs a WebSocketClient Driver to work."
            )

        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} "
                "doesn't support http client requests!"
                f"{self.get_name()} Adapter needs a HTTPClient Driver to work."
            )

        self.on_ready(self.startup)
        self.driver.on_shutdown(self.shutdown)

    async def shutdown(self) -> None:
        """关闭 Adapter"""
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *(asyncio.wait_for(task, timeout=10) for task in self.tasks),
            return_exceptions=True,
        )
        self.tasks.clear()

    async def startup(self) -> None:
        """启动 Adapter"""
        for bot_info in self.cx_config.cx_bots:
            task = asyncio.create_task(self.run_bot_websocket(bot_info))
            task.add_done_callback(self.tasks.discard)
            self.tasks.add(task)

    async def run_bot_websocket(self, bot_info: BotInfo) -> None:
        """连接 Bot"""
        bot = Bot(self, bot_info.im_user, bot_info)

        while True:
            try:
                async with self.websocket(
                    Request(
                        method="GET",
                        url="wss://im-api-vip6-v2.easemob.com/ws/{str1}/{str2}/websocket".format(
                            str1=int(random.random() * 1000),
                            str2="".join(random.choices("abcdefghijklmnopqrstuvwxyz012345", k=8)),
                        ),
                        timeout=None,
                    )
                ) as ws:
                    try:
                        await self._loop(bot, ws)
                    except WebSocketClosed as e:
                        log(
                            "ERROR",
                            "<r><bg #f8bbd0>WebSocket Closed</bg #f8bbd0></r>",
                            e,
                        )
                    except Exception as e:
                        log(
                            "ERROR",
                            (
                                "<r><bg #f8bbd0>"
                                "Error while process data from websocket "
                                "Trying to reconnect..."
                                "</bg #f8bbd0></r>"
                            ),
                            e,
                        )
                    finally:
                        if bot.self_id in self.bots:
                            self.bot_disconnect(bot)

            except Exception as e:
                log(
                    "ERROR",
                    ("<r><bg #f8bbd0>Error while setup websocketTrying to reconnect...</bg #f8bbd0></r>"),
                    e,
                )

            await asyncio.sleep(2)

    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Response:
        """调用平台 API"""

    def payload_to_event(self, payload: dict) -> Type[Event]:
        """将平台数据转换为 Event 对象"""

    async def _loop(self, bot: Bot, ws: WebSocket) -> None:
        """接收并处理 WebSocket 事件"""

        def _get_bytes_last_index(content: bytes, value: bytearray, start: int = 0, end: int = 0):
            length = len(value)
            len_bytes = len(content)
            if length == 0 or len_bytes == 0:
                return -1
            last = value[-1]
            for i in range(len_bytes - 1 if end == 0 else end - 1, start - 1, -1):
                if content[i] != last:
                    continue
                is_return = True
                for j in range(length - 2, -1, -1):
                    if content[i - length + j + 1] == value[j]:
                        continue
                    is_return = False
                    break
                if is_return:
                    return i - length + 1
            return -1

        def _get_bytes_index(content: bytes, value: bytearray, start=0, end=0):
            length = len(value)
            len_bytes = len(content)
            if length == 0 or len_bytes == 0:
                return -1
            first = value[0]
            for i in range(start, len_bytes if end == 0 else end):
                if content[i] != first:
                    continue
                is_return = True
                for j in range(1, length):
                    if content[i + j] == value[j]:
                        continue
                    is_return = False
                    break
                if is_return:
                    return i
            return -1

        def _get_chat_id(content: bytes):
            BYTES_ARRAY = bytearray(
                [
                    0x1A,
                    0x16,
                    0x63,
                    0x6F,
                    0x6E,
                    0x66,
                    0x65,
                    0x72,
                    0x65,
                    0x6E,
                    0x63,
                    0x65,
                    0x2E,
                    0x65,
                    0x61,
                    0x73,
                    0x65,
                    0x6D,
                    0x6F,
                    0x62,
                    0x2E,
                    0x63,
                    0x6F,
                    0x6D,
                ]
            )

            index = _get_bytes_last_index(
                content,
                BYTES_ARRAY,
            )
            if index == -1:
                return None
            i = content[:index].rfind(bytes([0x12]))
            if i == -1:
                return None
            length = content[i + 1]
            return content[i + 2 : index].decode("utf-8") if i + 2 + length == index else None

        def _get_attachment(content: bytes, start, end):
            BYTES_ATTACHMENT = bytearray(
                [0x0A, 0x61, 0x74, 0x74, 0x61, 0x63, 0x68, 0x6D, 0x65, 0x6E, 0x74, 0x10, 0x08, 0x32]
            )
            start = _get_bytes_index(content, BYTES_ATTACHMENT, start, end)
            if start == -1:
                return None
            start += len(BYTES_ATTACHMENT)
            length = content[start] + (content[start + 1] - 1) * 0x80
            start += 2
            s = start
            start += length
            e = start
            j = json.loads(content[s:e].decode("utf-8"))
            return None if start > end else j

        while True:
            data: str = await ws.receive()

            # 需要登录
            if data == "o":
                im_token = await bot.get_token()
                im_user = bot.bot_info.im_user
                timestamp = str(int(time.time() * 1000))
                temp = base64.b64encode(
                    b"\x08\x00\x12"
                    + chr(52 + len(im_user)).encode()
                    + b"\x0a\x0e"
                    + b"cx-dev#cxstudy"
                    + b"\x12"
                    + chr(len(im_user)).encode()
                    + im_user.encode()
                    + b"\x1a\x0b"
                    + b"easemob.com"
                    + b"\x22\x13"
                    + ("webim_" + timestamp).encode()
                    + b"\x1a\x85\x01"
                    + b"$t$"
                    + im_token.encode()
                    + b"\x40\x03\x4a\xc0\x01\x08\x10\x12\x05\x33\x2e\x30\x2e\x30\x28\x00\x30\x00\x4a\x0d"
                    + timestamp.encode()
                    + b"\x62\x05\x77\x65\x62\x69\x6d\x6a\x13\x77\x65\x62\x69\x6d\x5f"
                    + timestamp.encode()
                    + b"\x72\x85\x01\x24\x74\x24"
                    + im_token.encode()
                    + b"\x50\x00\x58\x00"
                )
                await ws.send(json.dumps([temp.decode()]))

            # 消息
            elif data[0] == "a":
                content = base64.b64decode(json.loads(data[1:])[0])

                if len(content) < 5:
                    return

                # 有新消息，调用根据环信消息ID获取消息详情函数获取消息详情
                if content[:5] == b"\x08\x00\x40\x02\x4a":
                    if _get_chat_id(content) is None:
                        return
                    msg = content.decode("utf-8")
                    temp = ""
                    for i in range(len(msg)):
                        if i == 3:
                            temp += b"\x00".decode()
                        elif i == 6:
                            temp += b"\x1a".decode()
                        else:
                            temp += msg[i]
                    mess2 = temp + bytearray([0x58, 0x00]).decode()
                    temp = base64.b64encode(mess2.encode())
                    await ws.send(json.dumps([temp.decode()]))

                # 首次与环信IM连接，获取未读消息
                elif content[:5] == b"\x08\x00\x40\x01\x4a":
                    if _get_chat_id(content) is None:
                        return
                    chatid_list: list[bytes] = re.findall(
                        b"\\x12-\\n\\)\\x12\\x0f(\\d+)\\x1a\\x16conference.easemob.com\\x10",
                        content,
                    )
                    for chatid in chatid_list:
                        temp = base64.b64encode(
                            b"\x08\x00@\x00J+\x1a)\x12\x0f" + chatid + b"\x1a\x16conference.easemob.comX\x00"
                        )
                        await ws.send(json.dumps([temp.decode()]))

                # 登录成功消息
                elif content[:5] == b"\x08\x00@\x03J":
                    await ws.send(json.dumps(["CABAAVgA"]))

                # 获取到消息详情，执行查找并提取签到消息函数
                else:
                    chatid = _get_chat_id(content)
                    if chatid is None:
                        return

                    sessonend = 11
                    while True:
                        index = sessonend
                        if chr(content[index]) != b"\x22".decode():
                            index += 1
                            break
                        else:
                            index += 1
                        sessonend = content[index] + (content[index + 1] - 1) * 0x80 + index + 2
                        index += 2
                        if sessonend < 0 or chr(content[index]).encode() != b"\x08":
                            index += 1
                            break
                        else:
                            index += 1

                        BYTES_END = bytearray(
                            [
                                0x1A,
                                0x16,
                                0x63,
                                0x6F,
                                0x6E,
                                0x66,
                                0x65,
                                0x72,
                                0x65,
                                0x6E,
                                0x63,
                                0x65,
                                0x2E,
                                0x65,
                                0x61,
                                0x73,
                                0x65,
                                0x6D,
                                0x6F,
                                0x62,
                                0x2E,
                                0x63,
                                0x6F,
                                0x6D,
                            ]
                        )

                        temp = base64.b64encode(
                            bytearray([0x08, 0x00, 0x40, 0x00, 0x4A])
                            + chr(len(chatid) + 38).encode()
                            + b"\x10"
                            + content[index : index + 9]
                            + bytearray([0x1A, 0x29, 0x12])
                            + chr(len(chatid)).encode()
                            + chatid.encode("utf-8")
                            + BYTES_END
                            + bytearray([0x58, 0x00])
                        )
                        await ws.send(json.dumps([temp.decode()]))
                        index += 10
                        att = _get_attachment(content, index, sessonend)
                        if att is not None:
                            ...
