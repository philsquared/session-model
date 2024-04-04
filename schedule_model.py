import datetime
import os
from dataclasses import dataclass, field
from functools import cached_property

from glassware.logging import log_warn
from pykyll.html import slugify, make_description
from pykyll.markdown import render_markdown
from pykyll.utils import common_suffix
from sessionmodel import Session as SessionModel

class Time:
    def __init__(self, time_str: str):
        parts = time_str.split(":")
        if len(parts) != 2:
            raise Exception(f"Invalid time: `{time_str}`")
        self.hour = int(parts[0])
        self.min = int(parts[1])

    @property
    def as_key(self):
        return f"{self.hour}_{self.min}"

    @property
    def total_minutes(self):
        return self.min * 60 + self.hour

    def __str__(self):
        return f"{self.hour}:{self.min}"

    def __repr__(self):
        return f"{self.hour}:{self.min}"

    def __lt__(self, other):
        return (self.hour < other.hour or
                (self.hour == other.hour) and self.min < other.min)


@dataclass
class Speaker:
    data: SessionModel.Speaker

    @property
    def bio_as_html(self):
        return render_markdown(self.data.bio, clean=True, strip_outer_p_tag=True, linkify=True)

    @property
    def profile_pic_path(self):
        # !TBD: extract the year
        if self.data.profile_pic:
            return os.path.join("/static", "img", "profiles", "2024", self.data.profile_pic )
        else:
            return None

    @property
    def header_image_path(self):
        # !TBD: extract the year
        if self.data.header_image:
            return os.path.join("/static", "img", "profiles", "2024", self.data.header_image )
        else:
            return None


@dataclass()
class Session:
    id: str
    live: bool
    data: SessionModel.Session

    start_time: Time
    end_time: Time

    # Indices into Timeslot times
    start_time_index = 0
    end_time_index = -1

    day: list = field(default_factory=list)  # Set after init

    _slug: str = None

    @property
    def is_workshop(self) -> bool:
        return self.data.type == "workshop"

    @property
    def duration_in_minutes(self):
        return self.end_time.total_minutes - self.start_time.total_minutes

    @property
    def length_description(self):
        if self.data.length.isnumeric():
            return f"{self.data.length} minute {self.data.type}"
        else:
            return self.data.length

    @property
    def speaker_names(self):
        names = [s.name for s in self.data.speakers]
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
        if self.data.speakers:
            return f"{self.data.title} - {self.speaker_names}"
        else:
            return self.data.title

    @property
    def title_as_html(self) -> str:
        return render_markdown(
            self.data.title,
            clean=True,
            strip_outer_p_tag=True,
            embedded_code=True,
            linkify=True,
            remove_elements=["h1", "h2", "h3"])

    @property
    def slug(self):
        if not self._slug:
            if self.data.slug:
                self._slug = self.data.slug
            else:
                self._slug = slugify(self.data.title)
        return self._slug

    @property
    def abstract_as_html(self) -> str:
        return render_markdown(self.data.abstract, linkify=True, clean=True, strip_outer_p_tag=True)

    @property
    def outline_as_html(self) -> str:
        return render_markdown(self.data.outline, linkify=True, clean=True, strip_outer_p_tag=True)

    @property
    def short_abstract_as_html(self) -> str:
        html = render_markdown(self.data.abstract, linkify=True, clean=True, strip_outer_p_tag=True)
        return make_description(html)

    @property
    def speakers(self):
        return [Speaker(s) for s in self.data.speakers]

    @property
    def header_image(self):
        if self.data.header_image:
            return os.path.join("/static", "img", self.data.header_image)
        image = None
        for speaker in self.speakers:
            if speaker.header_image_path is not None:
                if image is None:
                    image = os.path.join("/static", "img", "profiles", "2024", speaker.header_image_path)
                else:
                    log_warn("Multiple speakers have header images - selecting the first one")
        return image

    @property
    def date_range(self):
        if len(self.day) == 1:
            return f"{self.day[0].day}, {self.day[0].date_str}"
        elif len(self.day) > 1:
            date1 = self.day[0].date_str
            date2 = self.day[-1].date_str
            date1_parts = date1.split(" ")
            date2_parts = date2.split(" ")
            suffix = common_suffix(date1_parts, date2_parts)
            distinct_len = len(date1_parts) - len(suffix)
            date1 = " ".join(date1_parts[:distinct_len])
            date2 = " ".join(date2_parts[:distinct_len])
            date_common = " ".join(date1_parts[distinct_len:])
            return f"{self.day[0].day}, {date1} - {self.day[1].day}, {date2} {date_common}"
        else:
            raise Exception(f"Session, {self.slug} has no Day field")


# A timeslot for a room - usually  just one session, but may be multiple
@dataclass
class SessionSlot:
    index: int
    sessions: [Session]

    @property
    def is_single(self):
        return len(self.sessions) == 1


@dataclass
class Timeslot:
    times: [Time]
    type: str
    session_slots: [SessionSlot]

    @cached_property
    def has_speakers(self):
        for r in self.session_slots:
            for s in r.session_slots:
                if s.data.speakers:
                    return True
        return False

    @property
    def is_trackless(self):
        return len(self.session_slots) == 1


@dataclass
class Day:
    rooms: [int]

    # Day/ date in various formats
    day_num: int
    day: str
    date: datetime.date
    date_components: [int]
    date_str: str

    type: str
    label: str
    alt_label: str
    timeslots: [Timeslot]


@dataclass
class WorkshopGroup:
    name: str
    date_range: str
    workshops: [Session]


@dataclass
class Schedule:
    room_names: [str]
    default_header: str | None
    days: [Day]
    workshop_groups: [WorkshopGroup] = field(default_factory=list)
