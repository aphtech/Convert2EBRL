#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Optional print HTML of the issue, used when it is next to the BRF files.

The braille is always the source of the text. The print only refines what the braille cannot
show: exact link addresses, readable article ids and the level of section headings. Every use
is a fuzzy match on one item; anything that does not match well keeps the braille-only result."""
import difflib
import logging
import os
import re
import unicodedata
from dataclasses import dataclass
from functools import cache

import lxml.html

_PRINT_EXTENSIONS = (".htm", ".html")
_CHARSET_RE = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.I)
_TITLE_RATIO = 0.85
_LINK_RATIO = 0.9


@dataclass(frozen=True)
class PrintHeading:
    level: int
    text: str
    key: str
    slug: str


@dataclass
class PrintIssue:
    path: str
    title: str
    headings: list[PrintHeading]
    links: list[str]


def find_print_html(brf_path: str) -> str | None:
    """The print HTML in the BRF's folder: the only .htm/.html file, or the one named "Complete...".

    Folders such as "..._files" are not searched. Returns None when there is none or it is ambiguous."""
    folder = os.path.dirname(os.path.abspath(brf_path)) if brf_path else ""
    if not folder or not os.path.isdir(folder):
        return None
    candidates = sorted(f for f in os.listdir(folder)
                        if f.lower().endswith(_PRINT_EXTENSIONS) and os.path.isfile(os.path.join(folder, f)))
    if len(candidates) > 1:
        candidates = [f for f in candidates if f.lower().startswith("complete")]
    if len(candidates) == 1:
        return os.path.join(folder, candidates[0])
    if candidates:
        logging.warning("Several print HTML files in %s, so none is used: %s", folder, ", ".join(candidates))
    return None


def _decode(data: bytes) -> str:
    declared = _CHARSET_RE.search(data[:4096])
    for encoding in ([declared.group(1).decode("ascii")] if declared else []) + ["utf-8", "cp1252"]:
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode("cp1252", errors="replace")


def normalise(text: str) -> str:
    """Lower case words for comparing a back-translated braille heading with the print one."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub("[‘’']", "", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def slug(text: str) -> str:
    return normalise(text).replace(" ", "-")


@cache
def load_print_issue(path: str) -> PrintIssue | None:
    try:
        with open(path, "rb") as f:
            root = lxml.html.document_fromstring(_decode(f.read()))
    except (OSError, ValueError) as e:
        logging.warning("Could not read print file %s: %s", path, e)
        return None
    title = " ".join((root.findtext(".//title") or "").split())
    headings = []
    for element in root.iter("h1", "h2", "h3", "h4"):
        text = " ".join(element.text_content().split())
        level = int(element.tag[1])
        if not text or level == 1 or normalise(text) == "contents":
            continue
        headings.append(PrintHeading(level, text, normalise(text), slug(text)))
    links = []
    for a in root.iter("a"):
        href = (a.get("href") or "").strip()
        if href.lower().startswith(("http://", "https://", "mailto:")) and href not in links:
            links.append(href)
    return PrintIssue(path, title, headings, links)


def _best(key: str, candidates: list[tuple[str, object]], minimum: float):
    best, best_ratio = None, minimum
    for candidate_key, value in candidates:
        if candidate_key == key:
            return value
        ratio = difflib.SequenceMatcher(None, key, candidate_key).ratio()
        if ratio >= best_ratio:
            best, best_ratio = value, ratio
    return best


def match_heading(issue: PrintIssue, print_text: str, levels: tuple[int, ...]) -> PrintHeading | None:
    """The print heading of one of the levels most like the back-translated braille heading."""
    key = normalise(print_text)
    if not key:
        return None
    return _best(key, [(h.key, h) for h in issue.headings if h.level in levels], _TITLE_RATIO)


def _link_key(href: str) -> str:
    href = href.lower().strip()
    href = re.sub(r"^(?:https?://|mailto:)", "", href)
    href = re.sub(r"^www\.", "", href)
    return href.rstrip("/")


def match_link(issue: PrintIssue, href: str) -> str | None:
    """The print link for a back-translated address: an exact match ignoring scheme, www. and a
    final slash, else a very similar one (which corrects back-translation errors)."""
    key = _link_key(href)
    same_kind = [link for link in issue.links if link.lower().startswith("mailto:") == href.startswith("mailto:")]
    return _best(key, [(_link_key(link), link) for link in same_kind], _LINK_RATIO)
