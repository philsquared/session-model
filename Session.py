from dataclasses import dataclass
from functools import cached_property

from pykyll.html import slugify, make_description
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
    lead_presenter: int | None = None
    multi: bool = False  # Session spans multiple sessions/ days, so may appear multiple times but link to a single page
    reusable: bool = False  # Session is generic and may be reused, but link to unique pages
    slug: str | None = None
    header_image: str | None = None
    track: str | None = None
    _scheduled: bool = False
    sponsor: str | None = None

    @property
    def is_workshop(self) -> bool:
        return self.type == "workshop"

    @property
    def is_break(self) -> bool:
        return self.type == "break"

    @property
    def is_keynote(self) -> bool:
        return self.type == "keynote"

    @property
    def is_sponsored(self) -> bool:
        return self.type == "sponsored"


    @property
    def title_as_html(self) -> str:
        return render_markdown(
            self.title,
            clean=True,
            strip_outer_p_tag=True,
            embedded_code=True,
            linkify=True,
            remove_elements=["h1", "h2", "h3"])

    @property
    def speaker_names(self):
        names = [s.name for s in self.speakers]
        match len(names):
            case 0:
                return ""
            case 1:
                return names[0]
            case 2:
                return f"{names[0]} & {names[1]}"
            case _:
                return ", ".join(names[0:-1]) + f" & {names[-1]}"

    @property
    def title_slug(self):
        if self.slug:
            return self.slug
        else:
            return slugify(self.title)

    @property
    def abstract_as_html(self) -> str:
        return render_markdown(self.abstract, linkify=True, clean=True, strip_outer_p_tag=True)

    @property
    def outline_as_html(self) -> str:
        return render_markdown(self.outline, linkify=True, clean=True, strip_outer_p_tag=True)

    @cached_property
    def short_abstract_as_html(self) -> str:
        html = render_markdown(self.abstract, linkify=True, clean=True, strip_outer_p_tag=True)
        return make_description(html)
