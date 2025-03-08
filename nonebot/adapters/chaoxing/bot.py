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
from .config import BotInfo
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
    def __init__(self, adapter: "Adapter", self_id: str, bot_info: BotInfo):
        super().__init__(adapter, self_id)

        self.bot_info = bot_info

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
        """发送消息"""

    async def handle_event(self, event: Type[Event]):
        """处理事件"""
        if event.get_user_id() != self.self_id:
            await handle_event(self, event)

    async def send_private_msg(self, user_id: str, msg: str) -> None:
        """发送消息"""

    async def send_group_msg(self, group_id: str, msg: str) -> None:
        """发送消息"""

    @overload
    async def send_msg(self, user_id: str, msg: str) -> None: ...

    @overload
    async def send_msg(self, group_id: str, msg: str) -> None: ...

    async def send_msg(self, **kwargs) -> None:
        """发送消息"""

    async def get_token(self) -> str:
        """获取 Token"""
        if not self.bot_info.im_user or not self.bot_info.im_passwd:
            raise ValueError("im_user or im_passwd is empty")

        resp = await self.adapter.request(
            Request(
                method="POST",
                url="https://a1-vip6.easemob.com/cx-dev/cxstudy/token",
                json={
                    "grant_type": "password",
                    "password": self.bot_info.im_passwd,
                    "username": self.bot_info.im_user,
                },
            )
        )
        if resp.status_code != 200 or not resp.content:
            raise ValueError("Failed to get token")

        res: dict = json.loads(resp.content)
        if "access_token" not in res:
            raise ValueError("Failed to get token")

        return res["access_token"]
