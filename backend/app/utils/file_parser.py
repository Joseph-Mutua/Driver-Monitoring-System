from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ClipFile:
    original_name: str
    timestamp: str
    sequence: str
    stream_hint: str

    @property
    def seconds_of_day(self) -> int:
        if len(self.timestamp) == 6 and self.timestamp.isdigit():
            h = int(self.timestamp[0:2])
            m = int(self.timestamp[2:4])
            s = int(self.timestamp[4:6])
            return h * 3600 + m * 60 + s
        return 0


NAME_PATTERN = re.compile(
    r"^(?P<ts>\d{6})_(?P<seq>\d{3}_\d{3}_[A-Za-z0-9]+)(?P<rear>_rear)?\.mp4$",
    re.IGNORECASE,
)


def parse_clip_name(filename: str) -> ClipFile:
    match = NAME_PATTERN.match(filename)
    if not match:
        stem = filename.rsplit(".", 1)[0]
        return ClipFile(original_name=filename, timestamp=stem[:6], sequence="unknown", stream_hint="front")

    stream_hint = "rear" if match.group("rear") else "front"
    return ClipFile(
        original_name=filename,
        timestamp=match.group("ts"),
        sequence=match.group("seq"),
        stream_hint=stream_hint,
    )


def clip_sort_key(filename: str) -> tuple[int, str]:
    parsed = parse_clip_name(filename)
    return parsed.seconds_of_day, parsed.sequence
