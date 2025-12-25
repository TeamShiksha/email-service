from pydantic import BaseModel, field_validator
import re

HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

RGB_COLOR = re.compile(
    r"^rgba?\(\s*"
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\s*,\s*"
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)\s*,\s*"
    r"(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
    r"(?:\s*,\s*(0|1|0?\.\d+))?"
    r"\s*\)$"
)

class EmailTheme(BaseModel):
    fontFamily: str = "Inter, Arial, sans-serif"
    primaryColor: str = "#ac6aff"
    backgroundColor: str = "#141415"
    textColor: str = "#ffffff"
    buttonTextColor: str = "#ffffff"
    secondaryColor: str = "#ac6aff"

    @field_validator(
        "primaryColor",
        "backgroundColor",
        "textColor",
        "buttonTextColor",
        "fontFamily",
        "secondaryColor"
    )
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not (HEX_COLOR.match(value) or RGB_COLOR.match(value)):
            raise ValueError(
                "Invalid color format. Use HEX (#fff, #ffffff) or RGB/RGBA."
            )
        return value