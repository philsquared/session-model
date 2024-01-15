from dataclasses import dataclass, field

from pykyll.markdown import render_markdown
from sessionmodel.Colour import Colour
from sessionmodel.Link import Link


@dataclass
class Speaker:
    name: str
    friendly_name: str
    bio: str

    # These fields may be missing initially
    links: [Link]   # Social media/ website/ blog etc
    profile_pic: str | None = None
    header_image: str | None = None
    tint_colour: Colour | None = None
    tint_shade: str | None = None

    @property
    def bio_as_html(self):
        return render_markdown(self.bio, clean=True, strip_outer_p_tag=True)
