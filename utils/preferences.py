from enum import Enum
from json import loads
from pathlib import Path
from typing import Optional

from flet import ThemeMode
from pydantic import BaseModel, Field


class AccentColor(Enum):
    blue = "BLUE"
    red = "RED"
    pink = "PINK"
    purple = "PURPLE"
    indigo = "INDIGO"
    cyan = "CYAN"
    teal = "TEAL"
    green = "GREEN"
    lime = "LIME"
    yellow = "YELLOW"
    amber = "AMBER"
    orange = "ORANGE"

    brown = "BROWN"

    def __str__(self):
        return self.value


class DismissableContent(BaseModel):
    terms_of_service: bool = False
    performance_mode: bool = False
    advanced_mode: bool = False


class Directories(BaseModel):
    extract_from: Optional[Path] = None
    extract_to: Optional[Path] = None
    changes_to: Optional[Path] = None


class Preferences(BaseModel):
    path: Path
    theme: ThemeMode = Field(default=ThemeMode.DARK)
    accent_color: AccentColor = AccentColor.amber
    advanced_mode: bool = False
    performance_mode: bool = False
    changes_name_format: str = "%Y-%m-%d %H-%M-%S"
    directories: Directories = Field(default_factory=Directories)
    dismissables: DismissableContent = Field(default_factory=DismissableContent)

    @classmethod
    def load_from_json(cls, path: Path):
        if not path.exists():
            pref = cls(path=path)
            with open(path, "w+") as f:
                f.write(pref.json(indent=4))
            return pref
        try:
            data = loads(path.read_text())
            return cls.parse_obj(data)
        except Exception as e:
            pref = cls(path=path)
            with open(path, "w+") as f:
                f.write(pref.json(indent=4))
            return pref

    def save(self):
        with open(self.path, "w+") as f:
            f.write(self.json(indent=4))
