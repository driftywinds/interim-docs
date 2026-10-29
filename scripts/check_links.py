#!/usr/bin/env python3
"""Check internal links and anchors in the built site.

Run after `properdocs build`:

    python scripts/check_links.py

External URLs are not requested; they are reported only as a count.
"""

from __future__ import annotations

import html.parser
import pathlib
import sys
import urllib.parse

SITE = pathlib.Path("site")
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "javascript:", "data:", "//")


class PageParser(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.assets: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if value := values.get("id"):
            self.ids.add(value)
        if tag == "a" and (name := values.get("name")):
            self.ids.add(name)
        if href := values.get("href"):
            self.links.append(href)
        if tag in {"img", "script", "link", "source"}:
            for key in ("src", "href"):
                if value := values.get(key):
                    self.assets.append(value)


def resolve(page: pathlib.Path, url_path: str) -> pathlib.Path:
    """Resolve a URL path the way a static host would."""
    if url_path.startswith("/"):
        return (SITE / url_path.lstrip("/")).resolve()
    return (page.parent / url_path).resolve()


def target_html(path: pathlib.Path) -> pathlib.Path:
    """Map a URL path to the file Cloudflare Pages would serve."""
    if path.is_dir() or str(path).endswith("/") or path.suffix == "":
        return path / "index.html"
    return path


def main() -> int:
    if not SITE.is_dir():
        print("site/ not found; run `properdocs build` first", file=sys.stderr)
        return 2

    parsed: dict[pathlib.Path, PageParser] = {}
    for page in SITE.rglob("*.html"):
        parser = PageParser()
        parser.feed(page.read_text(encoding="utf-8"))
        parsed[page] = parser

    broken: list[str] = []
    external = 0

    for page, parser in parsed.items():
        for href in parser.links:
            if href.startswith(SKIP_SCHEMES):
                external += 1
                continue
            if not href or href.startswith("#"):
                fragment = href[1:]
                if fragment and fragment not in parser.ids:
                    broken.append(f"{page.relative_to(SITE)}: missing anchor #{fragment}")
                continue

            split = urllib.parse.urlsplit(href)
            if split.scheme or split.netloc:
                external += 1
                continue

            path = urllib.parse.unquote(split.path)
            resolved = resolve(page, path)
            target = target_html(resolved)
            if not target.exists():
                broken.append(f"{page.relative_to(SITE)}: {href} -> missing file")
                continue
            if split.fragment and target.suffix == ".html":
                target_parser = parsed.get(target)
                if target_parser and split.fragment not in target_parser.ids:
                    broken.append(f"{page.relative_to(SITE)}: {href} -> missing anchor")

        for asset in parser.assets:
            if asset.startswith(SKIP_SCHEMES):
                continue
            split = urllib.parse.urlsplit(asset)
            resolved = resolve(page, urllib.parse.unquote(split.path))
            if not resolved.exists():
                broken.append(f"{page.relative_to(SITE)}: {asset} -> missing asset")

    print(f"checked {len(parsed)} pages, {external} external links")
    if broken:
        print(f"\n{len(broken)} broken link(s):")
        for problem in sorted(set(broken)):
            print(f"  {problem}")
        return 1
    print("no broken internal links")
    return 0


if __name__ == "__main__":
    sys.exit(main())
