from dataclasses import dataclass

from sessionmodel.Speaker import Speaker


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
