from pydantic import BaseModel, field_validator
import re

HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

class EmailTheme(BaseModel):
    fontFamily: str = "Inter, Arial, sans-serif"
    primaryColor: str = "#ac6aff"
    backgroundColor: str = "#141415"
    textColor: str = "#ffffff"
    buttonTextColor: str = "#ffffff"

    @field_validator(
        "primaryColor",
        "backgroundColor",
        "textColor",
        "buttonTextColor",
        "fontFamily",
    )
    @classmethod
    def validate_hex_color(cls, value: str) -> str:
        # if not HEX_COLOR.match(value):
        #     raise ValueError("Invalid hex color")
        return value