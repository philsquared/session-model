import codecs
from dataclasses import asdict

import yaml

from .logging import log_warn
from objectipy.objectipy import dict_to_object
from sessionmodel.Link import Link
from sessionmodel.Session import Session
from sessionmodel.Speaker import Speaker


def _sessions_to_dict(sessions: [Session]) -> list:
    def null_filter_factory(data: list):
        return dict(x for x in data if x[1] is not None and not x[0].startswith("_"))
    return [asdict(session, dict_factory=null_filter_factory) for session in sessions]


def load_yaml(filename: str) -> dict:
    """
    Reads a YAML file into a dictionary
    """
    with codecs.open(filename, 'r', "utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(filename: str, data: dict):
    """
    Writes a dictionary to a YAML file
    """
    with codecs.open(filename, "w", "utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def save_sessions(filename: str, sessions: [Session]):
    """
    Writes an array of sessions to a YAML file
    """
    sessions = list(sessions)
    sessions.sort(key=lambda session: session.id)
    data = _sessions_to_dict(sessions)
    # with codecs.open(filename, "w", "utf-8") as f:
    #     for session in sessions:
    #         yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    save_yaml(filename, data)


def parse_sessions(sessions_data: [dict]) -> [Session]:
    """
    Parses an array of session data dicts into Session objects
    """
    sessions = [dict_to_object(session_data, Session) for session_data in sessions_data]

    #!TBD: once dict_to_objects recurses objects we can remove the next bit:
    for session in sessions:
        speakers = []
        for speaker_data in session.speakers:
            if links_data := speaker_data.get("links"):
                links = [dict_to_object(link_data, Link) for link_data in links_data]
                speaker_data["links"] = links
            if "bio" not in speaker_data:
                speaker_data["bio"] = "bio coming soon ..."
                log_warn(f"*** No bio found for speaker {speaker_data.get('name')} - defaulting")
            speaker = dict_to_object(speaker_data, Speaker)
            speakers.append(speaker)
        session.speakers = speakers
    return sessions


def load_sessions(filename: str) -> [Session]:
    """
    Reads an array of sessions from a YAML file and parses them into Session objects
    """
    data = load_yaml(filename)
    return parse_sessions(data)

