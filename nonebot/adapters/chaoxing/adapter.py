from typing import Any, Union, Callable, Optional, cast, Type, ClassVar
from pydantic import BaseModel, Field, ValidationError
from typing_extensions import override
from pathlib import Path
from yarl import URL
import contextlib
import asyncio
import hashlib
import secrets
import json
import sys
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
    ForwardDriver,
    ReverseDriver,
    HTTPClientMixin,
    HTTPServerSetup,
    WebSocketServerSetup,
)
from nonebot.adapters import Adapter as BaseAdapter

from .bot import Bot
from .event import *
from .utils import *
from .config import Config
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
        self.connections: dict[str, WebSocket] = {}
        self.access_token: dict[str, str] = {}
        self.tasks: set["asyncio.Task"] = set()
        self.cx_config: Config = get_plugin_config(Config)
        self._setup()

    @classmethod
    @override
    def get_name(cls) -> str:
        """ 适配器名称: `ChaoXing` """
        return "ChaoXing"

    def _setup(self) -> None:
        if not isinstance(self.driver, ASGIMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} doesn't support asgi server!"
                f"{self.get_name()} Adapter need a asgi server driver to work."
            )

        if not isinstance(self.driver, HTTPClientMixin):
            raise RuntimeError(
                f"Current driver {self.config.driver} "
                "doesn't support http client requests!"
                f"{self.get_name()} Adapter needs a HTTPClient Driver to work."
            )

        self.setup_http_server(
            HTTPServerSetup(
                path=URL("/chaoxing"),
                method="GET",
                name=f"{self.get_name()} Root GET",
                handle_func=self._handle_get,
            )
        )
        self.setup_http_server(
            HTTPServerSetup(
                path=URL("/chaoxing/"),
                method="GET",
                name=f"{self.get_name()} Root GET",
                handle_func=self._handle_get,
            )
        )

        self.setup_http_server(
            HTTPServerSetup(
                path=URL("/chaoxing/login"),
                method="POST",
                name=f"{self.get_name()} Root GET",
                handle_func=self._handle_login,
            )
        )

        self.setup_websocket_server(
            WebSocketServerSetup(
                path=URL("/chaoxing/ws"),
                name=f"{self.get_name()} Root WS",
                handle_func=self._handle_ws,
            )
        )

        self.driver.on_shutdown(self._shutdown)

    async def _shutdown(self) -> None:
        """ 关闭 Adapter """
        for task in self.tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(
            *(asyncio.wait_for(task, timeout=10) for task in self.tasks),
            return_exceptions=True,
        )
        self.tasks.clear()

    async def _call_api(self, bot: Bot, api: str, **data: Any) -> Response:
        """ 调用平台 API """
        body: Any | None = data.get("json", data.get("data", data.get("body", None)))

        request = Request(
            method=data.get("method", "POST"),
            url=f"https://api.weixin.qq.com/cgi-bin{api}",
            params=data.get("params", {}),
            headers={
                "Authorization": f"Bearer {self.access_token[bot.self_id]}",
            } | data.get("headers", {}),
            content=json.dumps(body, ensure_ascii=False).encode("utf-8") if body else None,
            files=data.get("files", None),
        )
        resp = await self.request(request)

        if resp.status_code != 200 or not resp.content:
            raise ActionFailed(resp)

        return resp

    async def _handle_ws(self, ws: WebSocket) -> None:
        """ 处理 WebSocket 连接 """
        self_id = ws.request.url.query.get("self_id")
        access_token = ws.request.url.query.get("access_token")

        if not self_id:
            log("WARNING", "Missing Self-ID")
            await ws.close(1008, "Missing Self-ID")
            return
        elif self_id in self.bots:
            log("WARNING", f"There's already a bot {self_id}, ignored")
            await ws.close(1008, "Duplicate Self-ID")
            return

        if self.cx_config.cx_token and access_token != self.cx_config.cx_token:
            log("WARNING", "Invalid access token")
            await ws.close(1008, "Invalid access token")
            return

        await ws.accept()
        bot = Bot(self, self_id)
        self.bot_connect(bot)
        self.connections[self_id] = ws

        log("INFO", f"<y>Bot {escape_tag(self_id)}</y> connected")

        try:
            while True:
                data = await ws.receive()
                payload: dict = json.loads(data)

                if event := self.payload_to_event(payload):
                    task = asyncio.create_task(bot.handle_event(event))
                    task.add_done_callback(self.tasks.discard)
                    self.tasks.add(task)
        except WebSocketClosed:
            log("WARNING", f"WebSocket for Bot {escape_tag(self_id)} closed by peer")
        except Exception as e:
            log(
                "ERROR",
                "<r><bg #f8bbd0>Error while process data from websocket "
                f"for bot {escape_tag(self_id)}.</bg #f8bbd0></r>",
                e,
            )
        finally:
            with contextlib.suppress(Exception):
                await ws.close()
            self.connections.pop(self_id, None)
            self.bot_disconnect(bot)

    async def _handle_get(self, request: Request) -> Response:
        """ 处理 HTTP GET 请求 """
        headers = {
            "Content-Type": "text/html; charset=utf-8",
        }
        if html := getattr(self, "_html", None):
            return Response(status_code=200, content=html, headers=headers)
        else:
            with open(Path(__file__).parent / "res" / "index.html", "r") as f:
                self._html = f.read()
            return Response(status_code=200, content=self._html, headers=headers)

    async def _handle_login(self, request: Request) -> Response:
        """ 处理登录请求 """
        data: dict = json.loads(request.content)

        im_username = data.get("im_username")
        im_password = data.get("im_password")

        if not im_username or not im_password:
            return Response(status_code=400, content="Missing im_username or im_password")

        resp = await self.request(
            Request(
                method="POST",
                url=URL("https://a1-vip6.easemob.com/cx-dev/cxstudy/token"),
                json={
                    "grant_type": "password",
                    "password": im_password,
                    "username": im_username,
                }
            )
        )
        res: dict = json.loads(resp.content)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        if access_token := res.get("access_token"):
            self.access_token[im_username] = cast(str, access_token)
            return Response(status_code=200, content=resp.content, headers=headers)
        else:
            return Response(status_code=400, content=resp.content, headers=headers)

    def payload_to_event(self, payload: dict) -> Type[Event]:
        """ 将平台数据转换为 Event 对象 """
        for cls in EVENT_CLASSES:
            try:
                event = cls.model_validate(payload)
                return event
            except ValidationError as e:
                pass
        raise UnkonwnEventError(payload)
