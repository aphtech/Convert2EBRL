#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Volume marker detectors."""

import re

from brf2ebrl import ParserContext

# "@.<,VOLUME " translated to Unicode Braille.
_VOLUME_MARKER_START = "⠈⠨⠣⠠⠧⠕⠇⠥⠍⠑⠀"
# "@.>" translated to Unicode Braille.
_VOLUME_MARKER_END = "⠈⠨⠜"

# eBraille has no need for volume markers, eg. "@.<,VOLUME #C@.>". The volume
# number is any legal Braille, so it is matched generically rather than as a
# specific number.
_VOLUME_MARKER_RE = re.compile(
    f"[ \t⠀]*{_VOLUME_MARKER_START}[⠁-⣿]+?{_VOLUME_MARKER_END}[ \t⠀]*\n?"
)


def remove_volume_markers(text: str, _: ParserContext = ParserContext()) -> str:
    """Remove volume markers since eBraille has no need for them."""
    return _VOLUME_MARKER_RE.sub("", text)
