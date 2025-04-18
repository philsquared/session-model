import os
from dataclasses import dataclass

import yaml

from sessionmodel.logging import log_info
from sessionmodel.schedule_model import Session, Timeslot, Schedule, Day, SessionSlot, Time, WorkshopGroup
from pykyll.utils import format_longdate, dict_merge
from sessionmodel.Sessions import load_yaml, parse_sessions

_schedules = {}

@dataclass
class ReusableSlug:
    slug: str
    count: int = 0

    def __str__(self):
        return f"{self.slug}-{self.count}"


class ScheduleBuilder:
    def __init__(self, session_data_by_id: dict):
        self.session_data_by_id = session_data_by_id
        self.reusable_slugs = {}
        self.session_by_slug = {}

    def read_session_slot(self, index: int, session_slot_entry, times: [Time], live: bool) -> SessionSlot:
        def make_session(session_id: str, times: [Time]) -> Session:
            session_info = self.session_data_by_id.get(session_id)
            if not session_info:
                raise Exception(f"No session data for {session_id}")
            session = Session(
                id=session_id,
                live=live,
                data=session_info,
                start_time=times[0],
                end_time=times[1])
            session_info.scheduled = True
            slug = session.slug
            if session_info.reusable:
                if (reusable_slug := self.reusable_slugs.get(slug)) is None:
                    reusable_slug = ReusableSlug(slug)
                    self.reusable_slugs[slug] = reusable_slug
                reusable_slug.count += 1
                session._slug = (slug := str(reusable_slug))
            if slug in self.session_by_slug:
                if session_info.multi:
                    session = self.session_by_slug[slug]
                    session.end_time = times[1]
                else:
                    raise Exception(f"Two sessions have the same slug, '{slug}'")
            else:
                self.session_by_slug[slug] = session
            return session

        if isinstance(session_slot_entry, dict):
            # explicit session_slot (alt start/ end times or multiple sessions)
            session_slot_data = session_slot_entry.get("session_slot")
            if not session_slot_data:
                raise Exception(f"Only 'session_slot' key currently supported, but found: {session_slot_entry.keys()}")

            sessions = [make_session(session_entry["session"], [Time(time) for time in session_entry.get("time")] or times) for session_entry in session_slot_data]
        else:
            # implicit session_slot - just one, full-length, session
            sessions = [make_session(session_slot_entry, times)]

        all_times = set()
        for session in sessions:
            if session.start_time >= times[0]:
                all_times.add(session.start_time)
            if session.end_time <= times[1]:
                all_times.add(session.end_time)
        all_times = sorted(all_times)

        return SessionSlot(index, sessions=sessions, times=all_times)

    def read_session_slots(self, session_slot_data, times: [Time], live_data: [int]) -> [SessionSlot]:
        return [self.read_session_slot(index, data, times, live == 1) for index, (data, live) in enumerate(zip(session_slot_data, live_data))]

    def read_timeslots(self, timeslot_data: [dict]) -> [Timeslot]:
        timeslots = []
        for time_num, data in enumerate(timeslot_data):
            sessions_data = data["sessions"]
            times = [Time(time_str) for time_str in data["time"]]
            live_data = data.get("live") or [0 for _ in sessions_data]
            session_slots = self.read_session_slots(sessions_data, times, live_data)
            times = set(times)
            for rs in session_slots:
                for s in rs.sessions:
                    if s.start_time >= rs.times[0]:
                        times.add(s.start_time)
                    if s.end_time <= rs.times[-1]:
                        times.add(s.end_time)
            times = list(times)
            times.sort()
            for rs in session_slots:
                rs.start_time_index = times.index(rs.times[0])
                rs.end_time_index = times.index(rs.times[-1])
                for s in rs.sessions:
                    try:
                        s.start_time_index = times.index(s.start_time)
                    except:
                        s.start_time_index = 0
                    try:
                        s.end_time_index = times.index(s.end_time)
                    except:
                        s.end_time_index = len(times)-1
            timeslot = Timeslot(
                times=times,
                type=data.get("type") or "sessions",
                session_slots=session_slots)

            timeslots.append(timeslot)
        return timeslots

    def read_days(self, day_data) -> [Day]:
        days = []
        for data in day_data:
            date = data["date"]
            day_num = data["day_num"]
            day = Day(
                rooms=data["rooms"],
                day_num=day_num,
                day=data["day"],
                date=date,
                date_str=format_longdate(date),
                date_components=[date.year, date.month-1, date.day],
                type=data.get("type") or "normal",
                label=data.get("label") or "",
                alt_label=data.get("alt_label") or "",
                timeslots = self.read_timeslots(data["timeslots"]))

            for timeslot in day.timeslots:
                session_count = len(timeslot.session_slots)
                room_count = len(day.rooms)
                if session_count > 1 and session_count != room_count:
                    raise Exception(f"Mismatch between number of rooms on {day.day} ({room_count}) and number of sessions at {timeslot.times[0]} ({session_count})")

            days.append(day)
        return days


def get_speakers_as_dict(session: dict) -> {str: dict}:
    if speakers := session.get("speakers"):
        return {speaker["id"]: speaker for speaker in speakers}
    else:
        return {}


def load_session_data(paths: [str]) -> {str: Session}:
    all_session_data = {}
    for path in paths:
        session_data = load_yaml(path)
        for session in session_data:
            if (session_id := session.get("id")) is None:
                raise Exception(f"session data has no ID:\n{session}")
            if existing_session := all_session_data.get(session_id):
                existing_speakers = get_speakers_as_dict(existing_session)
                new_speakers = get_speakers_as_dict(session)
                speakers = dict_merge(existing_speakers, new_speakers)
                session = dict_merge(existing_session, session)
                if speakers:
                    session["speakers"] = [s for s in speakers.values()]
            all_session_data[session_id] = session

    return {session.id: session for session in parse_sessions(all_session_data.values())}


def load_schedule(schedule_path: str | None, session_data_paths: [str], placeholder_profile: str | None = None) -> Schedule | None:
    session_data_by_id = load_session_data(session_data_paths)

    all_speakers = {}

    for session in session_data_by_id.values():
        for speaker in session.speakers:
            if speaker.id not in all_speakers:
                all_speakers[speaker.id] = speaker
                if speaker.profile_pic is None:
                    speaker.profile_pic = placeholder_profile

    builder = ScheduleBuilder(session_data_by_id)

    if schedule_path is None:
        return None

    with open(schedule_path, 'r') as f:
        data = yaml.safe_load(f)

    year = data["year"]
    schedule = Schedule(
        year=year,
        room_names=data["room_names"],
        default_header=data.get("default_header"),
        days=builder.read_days(data["days"]),
        tracks=data.get("tracks") or {},
        sessions_by_slug=builder.session_by_slug,
        all_sessions_by_id=session_data_by_id,
        speakers_by_id=all_speakers)

    workshops_seen = set()
    workshops = []
    for day in schedule.days:
        for timeslot in day.timeslots:
            for session_slots in timeslot.session_slots:
                room = schedule.room_names[day.rooms[session_slots.index]]
                for session in session_slots.sessions:
                    session.schedule = schedule
                    session.day.append(day)
                    session.room = room
                    if session.is_workshop:
                        if session.id not in workshops_seen:
                            workshops_seen.add(session.id)
                            workshops.append(session)
                    if session.data.track:
                        session.track = schedule.tracks[session.data.track]
                    if speakers := session.data.speakers:
                        if len(speakers) > 1:
                            speakers.sort(key=lambda s: s.id != session.data.lead_presenter)

    for workshop in workshops:
        date_range = workshop.date_range
        if not schedule.workshop_groups or schedule.workshop_groups[-1].date_range != date_range:
            group = WorkshopGroup(workshop.day[0].alt_label, date_range, [])
            schedule.workshop_groups.append(group)
        else:
            group = schedule.workshop_groups[-1]
        group.workshops.append(workshop)

    _schedules[str(year)] = schedule
    return schedule


def load_schedule_for_year(data_root: str, year: str):
    log_info(f"Loading {year} schedule")

    session_data_paths = [
        os.path.join(data_root, path)
        for path in [
            "fixed_session_data.yml",
            f"{year}/session_data.yml",
            f"{year}/session_data_overrides.yml",
        ]]

    load_schedule(
        schedule_path=os.path.join(data_root, f"{year}/schedule.yml"),
        session_data_paths=session_data_paths)
    log_info("Loaded")


def get_schedule(year: int) -> Schedule:
    return _schedules[str(year)]
