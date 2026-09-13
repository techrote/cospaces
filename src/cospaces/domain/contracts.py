"""Shared machine-contract primitives."""

from enum import IntEnum


class ExitStatus(IntEnum):
    SUCCESS = 0
    INTERNAL = 1
    USAGE = 2
    INFRASTRUCTURE = 3
    SELECTION = 4
    REMOTE = 5
    PERSISTENCE = 6
    VERIFICATION = 7
