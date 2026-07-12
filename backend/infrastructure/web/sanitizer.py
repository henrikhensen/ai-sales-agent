"""HTML sanitizer: extracts readable text, <title>, and meta description.

Uses only the standard library's ``html.parser`` — no third-party HTML
parsing dependency is needed for this deliberately simple, "good enough"
extraction. It never executes anything in the HTML: ``HTMLParser`` only
tokenises markup, script contents included, as plain text.
"""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser

#: Tags whose entire subtree (nested tags and text alike) is dropped —
#: never contributes to the extracted body text or title.
_SKIP_SUBTREE_TAGS = {"script", "style", "nav", "noscript", "template", "svg", "iframe"}

#: Layout/structural tags that only ever separate readable text — the tag
#: itself becomes a line break, but any nested text (e.g. inside a table
#: cell or list item) is still kept.
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "section", "article", "header",
    "footer", "main", "h1", "h2", "h3", "h4", "h5", "h6", "table", "tr",
    "td", "th", "blockquote", "pre",
}


@dataclass(frozen=True)
class ExtractedPage:
    """Readable content extracted from one HTML document."""

    title: str | None
    meta_description: str | None
    text: str
    # Whether a <meta name="viewport" ...> tag is present — a standard,
    # real proxy for "this page declares itself responsive/mobile-aware",
    # not a guess. Its absence is a genuine, common signal of an old site
    # built before mobile-first design was standard practice.
    has_viewport_meta: bool = False


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace within lines and drop blank lines."""
    lines = (" ".join(line.split()) for line in text.splitlines())
    non_empty_lines = [line for line in lines if line]
    return "\n".join(non_empty_lines)


class _ReadableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self.meta_description: str | None = None
        self.has_viewport_meta: bool = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_open_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing tags (e.g. <br/>, <meta/>) never open a subtree to skip.
        self._handle_open_tag(tag, attrs)

    def _handle_open_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_SUBTREE_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            attr_dict = {key.lower(): (value or "") for key, value in attrs}
            if attr_dict.get("name", "").lower() == "description" and attr_dict.get("content"):
                self.meta_description = attr_dict["content"].strip()
            if attr_dict.get("name", "").lower() == "viewport":
                self.has_viewport_meta = True
        if tag in _BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_SUBTREE_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag in _BLOCK_TAGS:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self._title_parts.append(data)
            return
        self._text_parts.append(data)

    def result(self) -> ExtractedPage:
        title = normalize_whitespace("".join(self._title_parts)) or None
        text = normalize_whitespace("".join(self._text_parts))
        return ExtractedPage(
            title=title,
            meta_description=self.meta_description,
            text=text,
            has_viewport_meta=self.has_viewport_meta,
        )


def extract_readable_text(html: str) -> ExtractedPage:
    """Extract readable body text, ``<title>``, and meta description from ``html``.

    Strips ``<script>``, ``<style>``, ``<nav>`` and a few similar noise tags
    entirely (tag and content both), then normalises whitespace. This is a
    deliberately simple, "good enough" extraction for human review — not a
    full readability/boilerplate-removal algorithm.
    """
    parser = _ReadableTextParser()
    parser.feed(html)
    parser.close()
    return parser.result()
