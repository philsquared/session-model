import codecs
from dataclasses import asdict

import yaml

from objectipy.objectipy import dict_to_object
from sessionmodel.Session import Session


def _sessions_to_dict(sessions: [Session]) -> list:
    def null_filter_factory(data: list):
        return dict(x for x in data if x[1] is not None)
    return [asdict(session, dict_factory=null_filter_factory) for session in sessions]


def save_sessions(sessions: [Session], filename: str):
    """
    Writes an array of sessions to a YAML file
    """
    data = _sessions_to_dict(sessions)
    with codecs.open(filename, "w", "utf-8") as f:
        yaml.dump(data, f, default_flow_style=False)


def load_sessions(filename: str) -> [Session]:
    """
    Reads an array of sessions from a YAML file
    """
    with codecs.open(filename, 'r', "utf-8") as f:
        data = yaml.safe_load(f)

    sessions = [dict_to_object(session_data, Session) for session_data in data]
    return sessions
