from dataclasses import dataclass

import yaml

from sessionmodel.schedule_model import Session, Timeslot, Schedule, Day, SessionSlot, Time, WorkshopGroup
from pykyll.markdown import render_markdown
from pykyll.utils import format_longdate
from sessionmodel.Sessions import load_sessions


schedule = None
session_by_slug = {}
reusable_slugs = {}


@dataclass
class ReusableSlug:
    slug: str
    count: int = 0

    def __str__(self):
        return f"{self.slug}-{self.count}"

all_speakers = {}

class ScheduleBuilder:
    def __init__(self, session_data_by_id: dict):
        self.session_data_by_id = session_data_by_id

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
            slug = session.slug
            if session_info.reusable:
                if (reusable_slug := reusable_slugs.get(slug)) is None:
                    reusable_slug = ReusableSlug(slug)
                    reusable_slugs[slug] = reusable_slug
                reusable_slug.count += 1
                session._slug = (slug := str(reusable_slug))
            if slug in session_by_slug:
                if session_info.multi:
                    session = session_by_slug[slug]
                else:
                    raise Exception(f"Two sessions have the same slug, '{slug}'")
            else:
                session_by_slug[slug] = session
            return session

        if isinstance(session_slot_entry, dict):
            # explicit session_slot (alt start/ end times or multiple sessions)
            session_slot_data = session_slot_entry.get("session_slot")
            if not session_slot_data:
                raise Exception(f"Only 'session_slot' key currently supported, but found: {session_slot_entry.keys()}")

            sessions = [make_session(session_entry["session"], session_entry["time"]) for session_entry in session_slot_data]
            return SessionSlot(index, sessions=sessions)
        else:
            # implicit session_slot - just one, full-length, session
            return SessionSlot(index, sessions=[make_session(session_slot_entry, times)])

    def read_session_slots(self, session_slot_data, times: [Time], live_data: [int]) -> [SessionSlot]:
        return [self.read_session_slot(index, data, times, live == 1) for index, (data, live) in enumerate(zip(session_slot_data, live_data))]

    def read_timeslots(self, timeslot_data: [dict]) -> [Timeslot]:
        timeslots = []
        for time_num, data in enumerate(timeslot_data):
            sessions_data = data["sessions"]
            times = data["time"]
            live_data = data.get("live") or [0 for _ in sessions_data]
            session_slots = self.read_session_slots(sessions_data, times, live_data)
            times = set(times)
            for rs in session_slots:
                for s in rs.sessions:
                    times.add(s.start_time)
                    times.add(s.end_time)
            times = list(times)
            times.sort()
            for rs in session_slots:
                for s in rs.sessions:
                    s.start_time_index = times.index(s.start_time)
                    s.end_time_index = times.index(s.end_time)
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


def load_schedule(schedule_path: str | None, session_data_path: str, fixed_session_data_path: str | None, workshops_only=False):
    sessions = load_sessions(session_data_path)

    if fixed_session_data_path is not None:
        fixed_sessions = load_sessions(fixed_session_data_path)
        sessions = sessions + fixed_sessions

    for session in sessions:
        session.title = render_markdown(
            session.title,
            clean=True,
            strip_outer_p_tag=True,
            embedded_code=True,
            remove_elements=["h1", "h2", "h3"])
        for speaker in session.speakers:
            if speaker.id not in all_speakers:
                all_speakers[speaker.id] = speaker

    session_data_by_id = {session.id: session for session in sessions}
    builder = ScheduleBuilder(session_data_by_id)

    if schedule_path is None:
        return

    with open(schedule_path, 'r') as f:
        data = yaml.safe_load(f)

    if workshops_only:
        days = data["days"]
        workshop_days = []
        for day in days:
            if "workshop" in day["label"]:
                workshop_days.append(day)
        data["days"] = workshop_days


    global schedule
    schedule = Schedule(
        room_names=data["room_names"],
        default_header=data["default_header"],
        days=builder.read_days(data["days"]))

    workshops_seen = set()
    workshops = []
    for day in schedule.days:
        for timeslot in day.timeslots:
            for session_slots in timeslot.session_slots:
                for session in session_slots.sessions:
                    session.day.append(day)
                    if session.is_workshop:
                        if session.id not in workshops_seen:
                            workshops_seen.add(session.id)
                            workshops.append(session)

    for workshop in workshops:
        date_range = workshop.date_range
        if not schedule.workshop_groups or schedule.workshop_groups[-1].date_range != date_range:
            group = WorkshopGroup(workshop.day[0].alt_label, date_range, [])
            schedule.workshop_groups.append(group)
        else:
            group = schedule.workshop_groups[-1]
        group.workshops.append(workshop)
