#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Bundler that links the NFB TOC entries to their articles across volumes.

The volumes are kept in memory until close(), when every article heading id is known, then
written in their original order through the normal eBraille bundler."""
import difflib
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import AnyStr

import lxml.html

from brf2ebrl.plugin import EBrlZippedBundler
from brf2ebrl_nfb.toc import TOC_PLACEHOLDER_PREFIX

_PLACEHOLDER_LINK_RE = re.compile(f'<a href="#{TOC_PLACEHOLDER_PREFIX}\\d+">(.*?)</a>', re.S)
_TAG_RE = re.compile("<[^>]+>")
# "by" between the title and the author in a TOC entry, after the U+2800 to space conversion.
_BY_SEPARATOR_RE = re.compile(" \u2803\u283d ")
_FUZZY_TITLE_RATIO = 0.85
# The stylesheet every volume links to (see brf2ebrl.common.detectors.xhtml_fixup_detector).
_DEFAULT_CSS = "ebraille/css/default.css"
# The volumes have no charset declaration, so tell lxml they are UTF-8.
_UTF8_HTML_PARSER = lxml.html.HTMLParser(encoding="utf-8")


@dataclass(frozen=True)
class _Article:
    volume: int
    id: str
    key: str


def _key(text: str) -> str:
    """Compare braille text ignoring tags and every kind of space and line break."""
    return re.sub(r"\s|\u2800", "", _TAG_RE.sub("", text))


def _articles(volumes: Sequence[tuple[str, str]]) -> list[_Article]:
    articles = []
    for index, (_, data) in enumerate(volumes):
        root = lxml.html.document_fromstring(data.encode("utf-8"), parser=_UTF8_HTML_PARSER)
        for heading in root.iter("h1"):
            if "article-title" in (heading.get("class") or "").split() and heading.get("id"):
                articles.append(_Article(index, heading.get("id"), _key(heading.text_content())))
    return articles


def _find_article(entry_text: str, articles: list[_Article], start: int) -> int | None:
    """The first article from start whose title begins the entry ("title by author").

    Falls back to the most similar title, comparing with the entry text before its last "by"."""
    entry_key = _key(entry_text)
    for i in range(start, len(articles)):
        if articles[i].key and entry_key.startswith(articles[i].key):
            return i
    title_part = _BY_SEPARATOR_RE.split(entry_text)
    title_key = _key(" \u2803\u283d ".join(title_part[:-1]) if len(title_part) > 1 else entry_text)
    best, best_ratio = None, _FUZZY_TITLE_RATIO
    for i in range(start, len(articles)):
        ratio = difflib.SequenceMatcher(None, title_key, articles[i].key).ratio()
        if ratio > best_ratio:
            best, best_ratio = i, ratio
    return best


def resolve_toc_links(volumes: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    """Replace the TOC placeholder links with links to the article headings."""
    articles = _articles(volumes)
    resolved = []
    for index, (name, data) in enumerate(volumes):
        next_article = 0

        def replace(m: re.Match[str]) -> str:
            nonlocal next_article
            found = _find_article(m.group(1), articles, next_article)
            if found is None:
                logging.warning("No article found for TOC entry %r in %s; left unlinked.",
                                _TAG_RE.sub("", m.group(1)), name)
                return m.group(1)
            next_article = found + 1
            article = articles[found]
            target_file = "" if article.volume == index else volumes[article.volume][0]
            return f'<a href="{target_file}#{article.id}">{m.group(1)}</a>'

        resolved.append((name, _PLACEHOLDER_LINK_RE.sub(replace, data)))
    return resolved


def _unlink_placeholders(volumes: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    return [(name, _PLACEHOLDER_LINK_RE.sub(lambda m: m.group(1), data)) for name, data in volumes]


class NfbZippedBundler(EBrlZippedBundler):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._volumes: list[tuple[str, str]] = []

    def write_file(self, name: str, path, add_to_spine: bool, *args, **kwargs):
        # The newsletter has its own default stylesheet in place of the library's.
        if Path(name).as_posix() == _DEFAULT_CSS:
            path = resources.files("brf2ebrl_nfb").joinpath("css", "default.css")
        super().write_file(name, path, add_to_spine, *args, **kwargs)

    def write_volume(self, name: str, data: AnyStr):
        self._volumes.append((name, data.decode("utf-8") if isinstance(data, bytes) else data))

    def close(self):
        try:
            try:
                volumes = resolve_toc_links(self._volumes)
            except Exception:
                logging.exception("Could not link the TOC entries; writing them unlinked.")
                volumes = _unlink_placeholders(self._volumes)
            for name, data in volumes:
                super().write_volume(name, data)
        finally:
            super().close()
