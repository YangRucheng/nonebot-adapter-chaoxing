from typing import Type, Union, Mapping, Iterable, Optional, Self, TYPE_CHECKING
from typing_extensions import override
from pydantic import HttpUrl
from pathlib import Path
from enum import Enum

from .exception import *
from nonebot.adapters import (
    MessageSegment as BaseMessageSegment,
    Message as BaseMessage,
)
if TYPE_CHECKING:
    from .event import MessageEvent


class MessageSegment(BaseMessageSegment["Message"]):
    """ 消息段 """

    @classmethod
    @override
    def get_message_class(cls) -> Type["Message"]:
        return Message

    @override
    def __str__(self) -> str:
        if self.type == "text":
            return self.data["text"]
        return ""

    @override
    def is_text(self) -> bool:
        return self.type == "text"

    @classmethod
    def text(
        cls,
        text: str,
        ext: dict = {},
    ) -> "Text":
        """ 文本消息段

        参数：
        - `text` 文本内容
        - `ext` 扩展字段
        """
        return Text("text", {
            "text": text,
            "ext": ext,
        })

    @classmethod
    def image(
        cls,
        file_url: Optional[HttpUrl] = None,
        file_name: Optional[str] = None,
        ext: dict = {},
    ) -> "Image":
        """ 图片消息段

        参数：
        - `file_url` 图片文件的网络 URL
        - `file_name` 图片文件名
        - `ext` 扩展字段
        """
        return Image("image", {
            "file_url": file_url,
            "file_name": file_name,
            "ext": ext,
        })

    @classmethod
    def voice(
        cls,
        file_url: Optional[HttpUrl] = None,
        file_name: Optional[str] = None,
        ext: dict = {},
    ) -> "Voice":
        """ 语音消息段

        参数：
        - `file_url` 语音文件的网络 URL
        - `file_name` 语音文件名
        - `ext` 扩展字段
        """
        return Voice("voice", {
            "file_url": file_url,
            "file_name": file_name,
            "ext": ext,
        })


class Text(MessageSegment):
    """ 文本 消息段 """


class Image(MessageSegment):
    """ 图片 消息段 """


class Voice(MessageSegment):
    """ 音频 消息段 """


class Message(BaseMessage[MessageSegment]):
    """ 消息 """

    @override
    @classmethod
    def get_segment_class(cls) -> Type[MessageSegment]:
        """ 获取消息段类 """
        return MessageSegment

    @override
    @staticmethod
    def _construct(msg: str) -> Iterable[MessageSegment]:
        """ 将文本消息构造成消息段数组 """
        yield Text("text", {"text": msg})

    @override
    def __add__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return super().__add__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    @override
    def __radd__(
        self, other: Union[str, "MessageSegment", Iterable["MessageSegment"]]
    ) -> "Message":
        return super().__radd__(
            MessageSegment.text(other) if isinstance(other, str) else other
        )

    def extract_plain_text(self) -> str:
        """ 提取消息中的纯文本 """
        return "".join(
            seg.data["text"]
            for seg in self
            if seg.type == "text"
        )

    @classmethod
    def from_event(cls, event: type["MessageEvent"]) -> "Message":
        """ 从消息事件转为消息序列 """
        if event.content_type == "text":
            return cls(
                MessageSegment.text(
                    text=getattr(event, "content", ""),
                    ext=event.ext,
                ),
            )
        elif event.content_type == "image":
            return cls(
                MessageSegment.image(
                    file_url=getattr(event, "file_url", ""),
                    ext=event.ext,
                ),
            )
        elif event.content_type == "voice":
            return cls(
                MessageSegment.voice(
                    file_url=getattr(event, "file_url", ""),
                    ext=event.ext,
                ),
            )
        else:
            raise ValueError(f"Unknown content type: {event.content_type}")
