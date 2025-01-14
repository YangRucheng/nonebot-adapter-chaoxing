from pydantic import Field, HttpUrl, BaseModel
from typing import Literal


class Config(BaseModel):
    cx_token: str = Field(default=None)  # access_token
