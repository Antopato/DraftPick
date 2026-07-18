from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RoomCreate(BaseModel):
    mode: Literal["standard", "fearless"] = "standard"
    best_of: Literal[1, 3, 5] = 1
    timer_seconds: int = Field(default=30, ge=5, le=180)
    blue_name: str | None = Field(default=None, max_length=40)
    red_name: str | None = Field(default=None, max_length=40)

    @model_validator(mode="after")
    def standard_is_bo1(self) -> "RoomCreate":
        if self.mode == "standard":
            self.best_of = 1
        return self


class RoomLinks(BaseModel):
    room_id: str
    blue_token: str
    red_token: str
    spectator_token: str
