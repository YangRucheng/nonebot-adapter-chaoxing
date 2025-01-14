from typing import Any, Union, Callable, Optional, cast, Literal, Type, TYPE_CHECKING
from pydantic import Field, ConfigDict, ValidationError, BaseModel, model_validator, HttpUrl
from typing_extensions import override
import datetime
import random

from nonebot.adapters import Event as BaseEvent
from nonebot.compat import model_dump

from .message import Message
from .utils import escape


class Event(BaseEvent):
    model_config = ConfigDict(extra='allow')

    @override
    def is_tome(self) -> bool:
        return False

    @override
    def get_type(self) -> Literal["message", "notice", "request", "meta_event"]:
        raise NotImplementedError

    @override
    def get_message(self) -> Optional["Message"]:
        raise NotImplementedError

    @override
    def get_event_name(self) -> str:
        return self.__class__.__name__

    @override
    def get_event_description(self) -> str:
        return str(model_dump(self))

    @override
    def get_user_id(self) -> str:
        raise NotImplementedError

    @override
    def get_session_id(self) -> str:
        raise NotImplementedError

    def get_event_id(self) -> str:
        raise NotImplementedError


class MetaEvent(Event):
    """ 元事件 """

    @override
    def get_type(self) -> Literal["meta_event"]:
        return "meta_event"


class NoticeEvent(Event):
    """ 通知事件 """

    @override
    def get_type(self) -> Literal["notice"]:
        return "notice"


class MessageEvent(Event):
    """ 消息事件 """
    message_id: str = Field(alias="id")
    """ 消息ID """
    message_type: Literal["private", "group"] = Field(alias="type")
    """ 消息类型 """
    user_id: str = Field(alias="from")
    """ 发送者ID """
    self_id: str = Field(alias="to")
    """ 接收者ID """
    content_type: Literal["text", "image", "voice"] = Field(alias="contentsType")
    """ 消息内容类型 """
    timestamp: int = Field(alias="time")
    """ 时间戳 """
    ext: dict = Field(default_factory=dict)
    """ 额外信息 """

    model_config = ConfigDict(extra='ignore')

    @model_validator(mode='before')
    def _(cls, values: dict[str, Any]) -> dict[str, Any]:
        """ 数据预处理 """
        if _type := values.get("type"):
            values["type"] = {
                "chat": "private",
                "groupchat": "group",
            }.get(_type, _type)

        values["contentsType"] = cast(str, values.get("contentsType", "")).lower()
        return values

    @property
    def time(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(self.timestamp / 1000)

    @property
    def message(self) -> Message:
        return self.get_message()

    @property
    def group_id(self) -> Optional[str]:
        """ 获取群聊ID """
        return self.get_group_id()

    @override
    def is_tome(self) -> bool:
        return getattr(self, "tome", False)

    @override
    def get_type(self) -> Literal["message"]:
        return "message"

    @override
    def get_message(self) -> Message:
        return Message.from_event(self)

    @override
    def get_event_description(self) -> str:
        keys = ('user_id', 'self_id', 'time', 'message_type', 'message_id', 'message')
        return str({key: getattr(self, key) for key in keys})

    @override
    def get_user_id(self) -> str:
        return str(self.user_id)

    def get_group_id(self) -> Optional[str]:
        """ 获取群聊ID """
        if self.message_type == "group":
            return self.self_id
        return None

    @override
    def get_session_id(self) -> str:
        return f"{self.user_id}_{self.self_id}"

    @override
    def get_event_id(self) -> str:
        return f"{self.message_id}_{self.get_session_id()}"


class CommandEvent(Event):
    """ 指令事件 """
    message_id: str = Field(alias="id")
    """ 消息ID """
    user_id: str = Field(alias="from")
    """ 发送者ID """
    self_id: str = Field(alias="to")
    """ 接收者ID """
    content_type: Literal["command"] = Field(alias="contentsType")
    """ 消息内容类型 """
    timestamp: int = Field(alias="time")
    """ 时间戳 """
    action: str = Field()
    """ 指令动作 """
    ext: dict = Field(default_factory=dict)
    """ 额外信息 """

    model_config = ConfigDict(extra='ignore')

    @model_validator(mode='before')
    def _(cls, values: dict[str, Any]) -> dict[str, Any]:
        """ 数据预处理 """
        if _type := values.get("type"):
            values["type"] = {
                "chat": "private",
                "groupchat": "group",
            }.get(_type, _type)

        values["contentsType"] = cast(str, values.get("contentsType", "")).lower()
        return values

    @override
    def get_type(self) -> Literal["message"]:
        return "request"


class ConnectedEvent(MetaEvent):
    """ 连接事件 """
    type: Literal["connected"] = Field()


class ClosedEvent(MetaEvent):
    """ 关闭事件 """
    type: Literal["closed"] = Field()


class ErrorEvent(MetaEvent):
    """ 错误事件 """
    type: Literal["error"] = Field()
    data: dict = Field()


class TextMessageEvent(MessageEvent):
    """ 文本消息事件 """
    content_type: Literal["text"] = Field(alias="contentsType")
    """ 消息内容类型 """
    content: str = Field(alias="data")
    """ 消息内容 """


class ImageMessageEvent(MessageEvent):
    content_type: Literal["image"] = Field(alias="contentsType")
    """ 消息内容类型 """
    file_url: HttpUrl = Field(alias="url")
    """ 图片URL """
    file_name: str = Field(alias="filename")
    """ 图片名称 """
    file_length: int = Field(alias="file_length")
    """ 图片大小 """
    file_width: int = Field(alias="width")
    """ 图片宽度 """
    file_height: int = Field(alias="height")
    """ 图片高度 """

    @model_validator(mode="before")
    def _(cls, values: dict[str, Any]) -> dict[str, Any]:
        """ 数据预处理 """
        values["file_length"] = int(values.get("file_length", 0) or 0)
        return values


class VoiceMessageEvent(MessageEvent):
    content_type: Literal["voice"] = Field(alias="contentsType")
    """ 消息内容类型 """
    file_url: HttpUrl = Field(alias="url")
    """ 音频URL """
    file_name: str = Field(alias="filename")
    """ 音频名称 """
    file_length: int = Field(alias="file_length")
    """ 音频大小 """


EVENT_CLASSES: list[type[Event]] = [
    ConnectedEvent,
    ClosedEvent,
    ErrorEvent,

    TextMessageEvent,
    ImageMessageEvent,
    VoiceMessageEvent,

    CommandEvent,
]
