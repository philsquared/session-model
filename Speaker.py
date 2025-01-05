from dataclasses import dataclass

from sessionmodel.Colour import Colour
from sessionmodel.Link import Link


@dataclass
class Speaker:
    id: int
    name: str
    friendly_name: str
    bio: str

    # These fields may be missing initially
    links: [Link]   # Social media/ website/ blog etc
    profile_pic: str | None = None
    header_image: str | None = None
    tint_colour: Colour | None = None
    tint_shade: str | None = None

    is_lead_presenter: bool = True

    @property
    def name_in_caps(self):
        return self.name.upper()
