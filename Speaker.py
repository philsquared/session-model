from dataclasses import dataclass, field

from Colour import Colour
from Link import Link


@dataclass
class Speaker:
    name: str
    friendly_name: str
    bio: str

    # These fields may be missing initially
    links: [Link] = field(default_factory=list)  # Social media/ website/ blog etc
    profile_pic: str | None = None
    header_image: str | None = None
    tint_colour: Colour | None = None
    tint_shade: str | None = None