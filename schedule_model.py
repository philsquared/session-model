import datetime
import os
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from .logging import log_warn
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
        return f"{self.hour:02d}:{self.min:02d}"

    def __repr__(self):
        return f"{self.hour:02d}:{self.min:02d}"

    def __lt__(self, other):
        return (self.hour < other.hour or
                (self.hour == other.hour) and self.min < other.min)

    def __le__(self, other):
        return self.hour < other.hour or (self.hour == other.hour and self.min <= other.min)

    def __ge__(self, other):
        return self.hour > other.hour or (self.hour == other.hour and self.min >= other.min)

    def __eq__(self, other):
        return  self.hour == other.hour and self.min == other.min

    def __hash__(self):
        return self.__str__().__hash__()


class Speaker:

    def __init__(self, data: SessionModel.Speaker):
        self.data = data

    @property
    def bio_as_html(self):
        return render_markdown(self.data.bio, clean=True, strip_outer_p_tag=True, linkify=True)

    @property
    def profile_pic_path(self):
        assert(False)
        # This has been removed

    @property
    def header_image_path(self):
        assert(False)
        # This has been removed


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
    room: str = "" # Set after init

    track: {} = field(default_factory=dict)
    _slug: str = None

    schedule: Any = None

    @property
    def is_workshop(self) -> bool:
        return self.data.is_workshop

    @property
    def is_break(self) -> bool:
        return self.data.is_break

    @property
    def is_keynote(self) -> bool:
        return self.data.is_keynote

    @property
    def is_sponsored(self) -> bool:
        return self.data.is_sponsored

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
        return self.data.speaker_names

    @property
    def title_prefix(self):
        if self.is_keynote:
            return "KEYNOTE: "
        elif self.is_sponsored:
            return "SPONSORED: "
        else:
            return ""

    @property
    def title_with_names(self):
        if self.data.speakers:
            return f"{self.data.title} - {self.speaker_names}"
        else:
            return self.data.title

    @property
    def title_as_html(self) -> str:
        return self.data.title_as_html

    @property
    def escaped_title(self) -> str:
        return self.data.title_as_html

    @property
    def slug(self):
        if not self._slug:
            self._slug = slugify(self.data.title)
        return self._slug

    @property
    def abstract_as_html(self) -> str:
        return self.data.abstract_as_html

    @property
    def outline_as_html(self) -> str:
        return self.data.outline_as_html

    @property
    def short_abstract_as_html(self) -> str:
        return self.data.short_abstract_as_html

    @property
    def speakers(self):
        return [Speaker(s) for s in self.data.speakers]

    @property
    def speaker_image(self):
        if self.data.speakers:
            for speaker in self.data.speakers:
                if speaker.profile_pic and "placeholder" not in speaker.profile_pic:  # !TBD: remove this hard coded string
                    return speaker.profile_pic
        return None

    @property
    def single_day(self) -> bool:
        return len(self.day) == 1

    @property
    def header_image(self):
        if self.data.header_image:
            return self.data.header_image
        image = None
        for speaker in self.speakers:
            if speaker.data.header_image is not None:
                if image is None:
                    image = speaker.data.header_image
                else:
                    log_warn("Multiple speakers have header images - selecting the first one")
        return image

    @property
    def date_range(self):
        if self.single_day:
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

    @property
    def full_time_desc(self) -> str:
        return f"{self.start_time}-{self.end_time}, {self.date_range}"

    @property
    def short_time_desc(self) -> str:
        if self.single_day:
            return f"{self.start_time}-{self.end_time}"
        else:
            return f"{self.start_time}-{self.end_time}, {self.date_range}"


# A timeslot for a room - usually  just one session, but may be multiple
@dataclass
class SessionSlot:
    index: int
    sessions: [Session]
    times: [Time]
    start_time_index: int = 0
    end_time_index: int = 1

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
    year: int
    room_names: list[str]
    default_header: str | None
    days: list[Day]
    tracks: dict
    sessions_by_slug: dict[str, Session]
    all_sessions_by_id: dict[str, Session]
    speakers_by_id: dict[str, Speaker]
    workshop_groups: list[WorkshopGroup] = field(default_factory=list)

    @property
    def all_speakers(self) -> list[Speaker]:
        return self.speakers_by_id.values()
