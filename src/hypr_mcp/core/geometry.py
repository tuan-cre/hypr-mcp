"""Shared geometry types. All coordinate math lives here."""

import dataclasses
import re

_REGION_RE = re.compile(r"^(-?\d+),(-?\d+)\s+(\d+)x(\d+)$")


@dataclasses.dataclass(frozen=True)
class Region:
    x: int
    y: int
    w: int
    h: int

    def to_grim(self) -> str:
        return f"{self.x},{self.y} {self.w}x{self.h}"

    @classmethod
    def parse(cls, s: str) -> "Region":
        m = _REGION_RE.match(s.strip())
        if not m:
            raise ValueError(f"Bad region {s!r}, expected 'X,Y WxH'")
        return cls(*[int(g) for g in m.groups()])


def matches_selector(client: dict, selector: str) -> bool:
    """Match a hyprctl client by 'class:X', 'title:Y', 'address:0x...', or bare class."""
    from ..backend.events import norm_addr
    cls = str(client.get("class", ""))
    title = str(client.get("title", ""))
    if selector.startswith("class:"):
        return cls.lower() == selector[6:].lower()
    if selector.startswith("title:"):
        return selector[6:].lower() in title.lower()
    if selector.startswith("address:"):
        return norm_addr(str(client.get("address", ""))) == norm_addr(selector[8:])
    return cls.lower() == selector.lower()


def find_client(clients: list[dict], selector: str) -> dict | None:
    for c in clients:
        if matches_selector(c, selector):
            return c
    return None


def client_region(client: dict) -> Region:
    (x, y), (w, h) = client["at"], client["size"]
    return Region(int(x), int(y), int(w), int(h))
