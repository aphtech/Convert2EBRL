# brf2ebrl-nfb

brf2ebrl plugin for the NFB *Braille Monitor* newsletter. It converts the newsletter's compact BRF
layout to eBraille: no blank lines, article separator lines, bylines, photo captions, transcripts and
a TOC that links to the articles.

It reuses the BANA plugin's page and transcriber's note detectors. See
[nfb_plugin_newsletter_plan.md](../../nfb_plugin_newsletter_plan.md) for the design.

Use it from the CLI with `uv run --all-packages brf2ebrl --parser NFB -o out.ebrl bm*.brf`, or pick
"Convert NFB Braille Monitor BRF to eBraille" in the GUI's Converter box.
