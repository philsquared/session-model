from dataclasses import dataclass, field

from pykyll import markdown
from pykyll.markdown import render_markdown
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

    @property
    def length_description(self):
        if self.length.isnumeric():
            return f"{self.length} minute session"
        else:
            return self.length

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
                return ", ".join(names[0:-2]) + f" & {names[-1]}"

    @property
    def title_with_names(self):
        if self.speakers:
            return f"{self.title} - {self.speaker_names}"
        else:
            return self.title

    @property
    def title_as_html(self) -> str:
        return render_markdown(self.title, clean=True, strip_outer_p_tag=True)

    @property
    def abstract_as_html(self) -> str:
        return render_markdown(self.abstract, linkify=True, clean=True, strip_outer_p_tag=True)

    @property
    def outline_as_html(self) -> str:
        return render_markdown(self.outline, linkify=True, clean=True, strip_outer_p_tag=True)
