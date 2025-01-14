from typing import Union, Any, Optional, Type, TYPE_CHECKING, cast, Literal, overload
from typing_extensions import override
from xmltodict import unparse
from pathlib import Path
import json
import time

from nonebot.message import handle_event
from nonebot.utils import logger_wrapper
from nonebot.adapters import Bot as BaseBot
from nonebot.drivers import Request, Response
from nonebot.drivers import (
    Request,
    Response,
)

from .event import *
from .utils import log, escape
from .exception import ActionFailed
from .message import (
    Text,
    Image,
    Voice,
    Message,
    MessageSegment,
)

if TYPE_CHECKING:
    from .adapter import Adapter


class Bot(BaseBot):
    adapter: "Adapter"

    @override
    def __init__(self, adapter: "Adapter", self_id: str):
        super().__init__(adapter, self_id)

        # Bot 鉴权信息
        self._access_token: Optional[str] = None
        self._expires_in: Optional[int] = None

    @override
    async def send(
        self,
        event: Event,
        message: Union[str, Message, MessageSegment],
        **kwargs,
    ) -> Any:
        """ 发送消息 """
        if isinstance(message, str):
            message = Message(MessageSegment.text(message))
        elif isinstance(message, MessageSegment):
            message = Message(message)
        elif not isinstance(message, Message):
            raise ValueError("message type error")

        msg = message.extract_plain_text()

        if not msg:
            raise ValueError("Empty message")

        if group_id := getattr(event, "group_id", None):
            await self.send_group_msg(group_id, msg)
        elif user_id := getattr(event, "user_id", None):
            await self.send_private_msg(user_id, msg)
        else:
            raise ValueError("Unknown recipient: neither group_id nor user_id found in event")

    async def handle_event(self, event: Type[Event]):
        """ 处理事件 """
        await handle_event(self, event)

    async def send_private_msg(self, user_id: str, msg: str) -> None:
        """ 发送消息 """
        ws = self.adapter.connections[self.self_id]
        await ws.send_text(json.dumps({
            "chatType": "singleChat",
            "ext": {},
            "from": self.self_id,
            "id": random.randint(int(10e12), int(10e15)),
            "msg": msg,
            "to": user_id,
            "type": "txt",
        }))

    async def send_group_msg(self, group_id: str, msg: str) -> None:
        """ 发送消息 """
        ws = self.adapter.connections[self.self_id]
        await ws.send_text(json.dumps({
            "group": "groupchat",
            "ext": {},
            "from": self.self_id,
            "id": random.randint(int(10e12), int(10e15)),
            "msg": msg,
            "to": group_id,
            "type": "txt",
        }))

    @overload
    async def send_msg(self, user_id: str, msg: str) -> None:
        ...

    @overload
    async def send_msg(self, group_id: str, msg: str) -> None:
        ...

    async def send_msg(self, **kwargs) -> None:
        """ 发送消息 """
        if "user_id" in kwargs:
            await self.send_private_msg(kwargs["user_id"], kwargs["msg"])
        elif "group_id" in kwargs:
            await self.send_group_msg(kwargs["group_id"], kwargs["msg"])
        else:
            raise ValueError("Unknown message type")
