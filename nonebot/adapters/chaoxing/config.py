from pydantic import Field, BaseModel


class Config(BaseModel):
    cx_token: str = Field(default="")
