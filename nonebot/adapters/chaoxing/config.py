from pydantic import BaseModel, Field
from typing import Optional


class BotInfo(BaseModel):
    im_user: Optional[str] = None
    """超星IM用户名"""
    im_passwd: Optional[str] = None
    """超星IM密码"""


class Config(BaseModel):
    cx_bots: list[BotInfo] = Field(default_factory=list)
    """环信机器人配置列表"""
