from dataclasses import dataclass

from sessionmodel.Speaker import Speaker
from pykyll.markdown import render_markdown


@dataclass
class Session:
    id: str
    title: str
    abstract: str
    length: str | None
    audience: list[str]
    tags: list[str]
    speakers: list[Speaker]
    outline: str | None
    type: str = "session"
    multi: bool = False  # Session spans multiple sessions/ days, so may appear multiple times but link to a single page
    reusable: bool = False  # Session is generic and may be reused, but link to unique pages
    slug: str | None = None
    header_image: str | None = None
    track: str | None = None

    @property
    def is_workshop(self) -> bool:
        return self.type == "workshop"

    @property
    def title_as_html(self) -> str:
        return render_markdown(
            self.title,
            clean=True,
            strip_outer_p_tag=True,
            embedded_code=True,
            linkify=True,
            remove_elements=["h1", "h2", "h3"])
