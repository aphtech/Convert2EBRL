#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Link web addresses and email addresses in the NFB Braille Monitor.

The braille text of the address is kept as the link text; the href is back-translated from the
contracted braille (eg. ",COMMUNICA;NS@ANFB4ORG" gives mailto:communications@nfb.org)."""
import html
import re
from collections.abc import Callable

from brf2ebrl.parser import ParserContext, NotifyLevel
from brf2ebrl.utils.back_translation import back_translate_contracted
from brf2ebrl_nfb.print_source import PrintIssue, match_link

# Tags and processing instructions; the text between them is searched for addresses.
_TOKEN_RE = re.compile("(<[^>]*>)")
# The dots 5 line continuation indicator ending a line inside a long address.
_CONTINUATION = "\u2810\n"
# http:// or https://. Kept literally because the colon would back-translate as "cc".
_SCHEME_RE = re.compile("\u2813\u281e\u281e\u280f(\u280e?)\u2812\u2838\u280c\u2838\u280c")
# An address runs to the next space or line break, unless the line ends with the continuation indicator.
# An address starts after a space, a line break or an opening parenthesis.
_ADDRESS_START = "(?:(?<![^\u2800\n])|(?<=\u2810\u2823))"
_ADDRESS_BODY = "(?:\u2810\n|[\u2801-\u28ff])+"
_URL_RE = re.compile(f"{_ADDRESS_START}(?:\u2813\u281e\u281e\u280f\u280e?\u2812\u2838\u280c\u2838\u280c"
                     f"|\u283a\u283a\u283a\u2832){_ADDRESS_BODY}")
# An email address: a word containing @ (dots 4 then a).
_EMAIL_RE = re.compile(f"{_ADDRESS_START}[\u2801-\u28ff]+\u2808\u2801{_ADDRESS_BODY}")
_AT = "\u2808\u2801"
_DOT = "\u2832"
# Punctuation after an address that ends the sentence or clause rather than being part of it.
_TRAILING_PUNCTUATION = ("\u2810\u281c", "\u2820\u2834", "\u2832", "\u2802", "\u2806", "\u2812", "\u2816",
                         "\u2826", "\u2834")
_URL_CHECK_RE = re.compile(r"^https?://[a-z0-9][a-z0-9.-]*\.[a-z]{2,}(?:[/?#]\S*)?$")
_EMAIL_CHECK_RE = re.compile(r"^mailto:[^@\s/]+@[a-z0-9][a-z0-9.-]*\.[a-z]{2,}$")


def _strip_trailing_punctuation(address: str) -> str:
    stripped = True
    while stripped:
        stripped = False
        for punctuation in _TRAILING_PUNCTUATION:
            if address.endswith(punctuation) and len(address) > len(punctuation):
                address = address[:-len(punctuation)]
                stripped = True
    return address


def address_href(braille: str, is_email: bool,
                 back_translate: Callable[[str], str | None] = back_translate_contracted) -> str | None:
    """The href for a braille address, or None if it cannot be back-translated to a valid address."""
    braille = braille.replace(_CONTINUATION, "")
    if is_email:
        print_text = back_translate(braille)
        href = f"mailto:{print_text.lower()}" if print_text else None
        check = _EMAIL_CHECK_RE
    else:
        scheme = _SCHEME_RE.match(braille)
        print_text = back_translate(braille[scheme.end():] if scheme else braille)
        if print_text:
            # Braille capitals are not significant in the host, so lower case it.
            host, slash, path = print_text.partition("/")
            href = f"http{'s' if scheme is None or scheme.group(1) else ''}://{host.lower()}{slash}{path}"
        else:
            href = None
        check = _URL_CHECK_RE
    return href if href and check.match(href) else None


def _link_segment(segment: str, at_start_pi: bool, at_end_pi: bool, parser_context: ParserContext,
                  back_translate: Callable[[str], str | None], print_issue: PrintIssue | None,
                  stats: dict[str, int]) -> str:
    found: list[tuple[int, int, bool]] = []
    for regex, is_email in ((_URL_RE, False), (_EMAIL_RE, True)):
        for m in regex.finditer(segment):
            if not any(m.start() < end and start < m.end() for start, end, _ in found):
                found.append((m.start(), m.end(), is_email))
    result = []
    position = 0
    for start, end, is_email in sorted(found):
        address = _strip_trailing_punctuation(segment[start:end])
        # Not an email: no dot in the domain, or a social media handle such as @name@server.social.
        if is_email and (address.count(_AT) != 1 or _DOT not in address.split(_AT, 1)[1]):
            continue
        # A processing instruction (eg. a page break) right next to an address may split it, so
        # only part of the address would be here.
        if (at_end_pi and not segment[start + len(address):].strip("\u2800\n")) or \
                (at_start_pi and not segment[:start].strip("\u2800\n")):
            continue
        href = address_href(address, is_email, back_translate)
        stats["links"] += 1
        if href is not None and print_issue is not None and (print_href := match_link(print_issue, href)):
            # The print address is exact, so it also corrects any back-translation mistake.
            href = print_href
            stats["print_links"] += 1
        if href is None:
            parser_context.notify_str(NotifyLevel.WARN, "Could not work out the address for braille "
                                                        f"{address!r}, so it is not a link.")
            continue
        result.append(segment[position:start])
        result.append(f'<a href="{html.escape(href, quote=True)}">{address.replace(_CONTINUATION, "")}</a>')
        position = start + len(address)
    result.append(segment[position:])
    return "".join(result)


def create_link_pass(back_translate: Callable[[str], str | None] = back_translate_contracted,
                     print_issue: PrintIssue | None = None,
                     stats: dict[str, int] | None = None) -> Callable[[str, ParserContext], str]:
    """A parser pass linking addresses in text outside tags, processing instructions and existing links.

    With the print HTML, a link's address is replaced by the matching print address."""
    stats = stats if stats is not None else {}
    stats.setdefault("links", 0)
    stats.setdefault("print_links", 0)

    def tag_links(text: str, parser_context: ParserContext) -> str:
        tokens = _TOKEN_RE.split(text)
        in_link = 0
        for i in range(0, len(tokens), 2):
            if i > 0:
                tag = tokens[i - 1]
                if tag.startswith("<a ") or tag == "<a>":
                    in_link += 1
                elif tag == "</a>":
                    in_link = max(0, in_link - 1)
            if in_link or not tokens[i]:
                continue
            at_start_pi = i > 0 and tokens[i - 1].startswith("<?")
            at_end_pi = i + 1 < len(tokens) and tokens[i + 1].startswith("<?")
            tokens[i] = _link_segment(tokens[i], at_start_pi, at_end_pi, parser_context, back_translate,
                                      print_issue, stats)
        return "".join(tokens)

    return tag_links
