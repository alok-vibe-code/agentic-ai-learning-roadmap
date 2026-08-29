"""Deterministic, network-free SEO analysis used by the MCP adapter."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

from models import AuditIssue, Heading, LinkRecord, PageSnapshot


MAX_HTML_CHARS = 1_000_000
MAX_LINKS = 5_000
MAX_HEADINGS = 1_000
HTTP_SCHEMES = {"http", "https"}

TITLE_MIN = 30
TITLE_MAX = 60
META_MIN = 120
META_MAX = 160


def _clean_text(value: str) -> str:
    return " ".join(value.split()).strip()


def _attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {
        key.casefold(): (value or "")
        for key, value in attrs
    }


class SEOHTMLParser(HTMLParser):
    """Parse only the elements required for the demo SEO audit.

    HTMLParser treats page contents as data. It does not execute scripts.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.snapshot = PageSnapshot()
        self._in_title = False
        self._title_parts: list[str] = []
        self._heading_level: int | None = None
        self._heading_parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        tag = tag.casefold()
        values = _attrs_dict(attrs)

        if tag == "title":
            self._in_title = True
            self._title_parts = []

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            if len(self.snapshot.headings) < MAX_HEADINGS:
                self._heading_level = int(tag[1])
                self._heading_parts = []

        if tag == "meta":
            name = values.get("name", "").strip().casefold()
            content = _clean_text(values.get("content", ""))
            if name == "description" and content:
                self.snapshot.meta_descriptions.append(content)
            elif name == "robots" and content:
                self.snapshot.robots_values.append(content)
            elif name == "googlebot" and content:
                self.snapshot.googlebot_values.append(content)

        if tag == "link":
            rel_tokens = {
                token.casefold()
                for token in values.get("rel", "").split()
            }
            href = values.get("href", "").strip()
            if "canonical" in rel_tokens and href:
                self.snapshot.canonicals.append(href)

        if tag == "a" and len(self.snapshot.links) < MAX_LINKS:
            href = values.get("href", "").strip()
            if href:
                self.snapshot.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()

        if tag == "title" and self._in_title:
            self._in_title = False
            title = _clean_text(" ".join(self._title_parts))
            if title and self.snapshot.title is None:
                self.snapshot.title = title
            self._title_parts = []

        if (
            self._heading_level is not None
            and tag == f"h{self._heading_level}"
        ):
            text = _clean_text(" ".join(self._heading_parts))
            self.snapshot.headings.append(
                Heading(level=self._heading_level, text=text)
            )
            self._heading_level = None
            self._heading_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)

        if self._heading_level is not None:
            self._heading_parts.append(data)


def validate_html(html: str) -> str:
    if not isinstance(html, str):
        raise TypeError("html must be a string.")
    if len(html) > MAX_HTML_CHARS:
        raise ValueError(
            f"HTML input exceeds the {MAX_HTML_CHARS:,}-character demo limit."
        )
    return html


def parse_html(html: str) -> PageSnapshot:
    parser = SEOHTMLParser()
    parser.feed(validate_html(html))
    parser.close()
    return parser.snapshot


def _keyword_present(text: str | None, keyword: str) -> bool | None:
    cleaned_keyword = _clean_text(keyword).casefold()
    if not cleaned_keyword:
        return None
    return cleaned_keyword in (text or "").casefold()


def get_page_title(
    html: str,
    primary_keyword: str = "",
) -> dict:
    snapshot = parse_html(html)
    title = snapshot.title
    length = len(title) if title else 0

    issues: list[dict] = []
    if not title:
        issues.append({
            "code": "missing_title",
            "severity": "error",
            "message": "No <title> element with text was found.",
        })
    elif length < TITLE_MIN:
        issues.append({
            "code": "short_title",
            "severity": "warning",
            "message": (
                f"Title is {length} characters. The demo heuristic uses "
                f"{TITLE_MIN}-{TITLE_MAX} characters as a review range."
            ),
        })
    elif length > TITLE_MAX:
        issues.append({
            "code": "long_title",
            "severity": "warning",
            "message": (
                f"Title is {length} characters. The demo heuristic uses "
                f"{TITLE_MIN}-{TITLE_MAX} characters as a review range."
            ),
        })

    return {
        "title": title,
        "length": length,
        "review_range": {"min": TITLE_MIN, "max": TITLE_MAX},
        "primary_keyword": _clean_text(primary_keyword) or None,
        "keyword_present": _keyword_present(title, primary_keyword),
        "issues": issues,
        "note": (
            "Character ranges are review heuristics, not guaranteed search-result "
            "display limits or ranking rules."
        ),
    }


def get_meta_description(
    html: str,
    primary_keyword: str = "",
) -> dict:
    snapshot = parse_html(html)
    descriptions = snapshot.meta_descriptions
    description = descriptions[0] if descriptions else None
    length = len(description) if description else 0

    issues: list[dict] = []
    if not descriptions:
        issues.append({
            "code": "missing_meta_description",
            "severity": "warning",
            "message": "No meta description was found.",
        })
    elif len(descriptions) > 1:
        issues.append({
            "code": "multiple_meta_descriptions",
            "severity": "warning",
            "message": f"Found {len(descriptions)} meta descriptions.",
        })

    if description and length < META_MIN:
        issues.append({
            "code": "short_meta_description",
            "severity": "info",
            "message": (
                f"Description is {length} characters. The demo heuristic uses "
                f"{META_MIN}-{META_MAX} characters as a review range."
            ),
        })
    elif description and length > META_MAX:
        issues.append({
            "code": "long_meta_description",
            "severity": "info",
            "message": (
                f"Description is {length} characters. The demo heuristic uses "
                f"{META_MIN}-{META_MAX} characters as a review range."
            ),
        })

    return {
        "description": description,
        "all_descriptions": descriptions,
        "count": len(descriptions),
        "length": length,
        "review_range": {"min": META_MIN, "max": META_MAX},
        "primary_keyword": _clean_text(primary_keyword) or None,
        "keyword_present": _keyword_present(description, primary_keyword),
        "issues": issues,
        "note": (
            "Search engines may rewrite snippets. This length range is only a "
            "content-review heuristic."
        ),
    }


def _heading_hierarchy_issues(headings: list[Heading]) -> list[dict]:
    issues: list[dict] = []
    previous: int | None = None

    for index, heading in enumerate(headings, start=1):
        if previous is not None and heading.level > previous + 1:
            issues.append({
                "code": "heading_level_jump",
                "severity": "warning",
                "message": (
                    f"Heading #{index} jumps from H{previous} to H{heading.level}."
                ),
            })
        previous = heading.level

    return issues


def extract_headings(
    html: str,
    primary_keyword: str = "",
) -> dict:
    snapshot = parse_html(html)
    headings = snapshot.headings
    h1s = [heading.text for heading in headings if heading.level == 1]

    issues = _heading_hierarchy_issues(headings)
    if not h1s:
        issues.insert(0, {
            "code": "missing_h1",
            "severity": "warning",
            "message": "No H1 heading was found.",
        })
    elif len(h1s) > 1:
        issues.insert(0, {
            "code": "multiple_h1",
            "severity": "info",
            "message": f"Found {len(h1s)} H1 headings.",
        })

    keyword = _clean_text(primary_keyword)
    return {
        "headings": [
            {"level": heading.level, "text": heading.text}
            for heading in headings
        ],
        "count": len(headings),
        "h1_count": len(h1s),
        "h1_texts": h1s,
        "primary_keyword": keyword or None,
        "keyword_present_in_h1": (
            None
            if not keyword
            else any(keyword.casefold() in h1.casefold() for h1 in h1s)
        ),
        "issues": issues,
    }


def _normalize_http_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if parsed.scheme and parsed.scheme.casefold() not in HTTP_SCHEMES:
        raise ValueError("Only http:// and https:// URLs are supported.")
    return url.strip()


def get_canonical(
    html: str,
    page_url: str = "",
) -> dict:
    snapshot = parse_html(html)
    canonicals = snapshot.canonicals
    cleaned_page_url = _normalize_http_url(page_url) if page_url.strip() else ""

    resolved = [
        urljoin(cleaned_page_url, canonical) if cleaned_page_url else canonical
        for canonical in canonicals
    ]

    issues: list[dict] = []
    if not canonicals:
        issues.append({
            "code": "missing_canonical",
            "severity": "warning",
            "message": "No rel=canonical link was found.",
        })
    elif len(canonicals) > 1:
        issues.append({
            "code": "multiple_canonicals",
            "severity": "error",
            "message": f"Found {len(canonicals)} canonical links.",
        })

    if cleaned_page_url and resolved:
        page_host = (urlparse(cleaned_page_url).hostname or "").casefold()
        canonical_host = (urlparse(resolved[0]).hostname or "").casefold()
        if canonical_host and page_host and canonical_host != page_host:
            issues.append({
                "code": "cross_domain_canonical",
                "severity": "info",
                "message": (
                    f"Canonical host {canonical_host!r} differs from "
                    f"page host {page_host!r}."
                ),
            })

    return {
        "canonicals": canonicals,
        "resolved_canonicals": resolved,
        "count": len(canonicals),
        "page_url": cleaned_page_url or None,
        "issues": issues,
    }


def _classify_link(href: str, page_url: str) -> LinkRecord:
    stripped = href.strip()
    lower = stripped.casefold()

    if not stripped:
        return LinkRecord(href, href, "empty")
    if lower.startswith("#"):
        return LinkRecord(href, stripped, "fragment")
    if lower.startswith(("mailto:", "tel:", "javascript:", "data:")):
        return LinkRecord(href, stripped, "non_http")

    resolved = urljoin(page_url, stripped) if page_url else stripped
    parsed = urlparse(resolved)

    if parsed.scheme and parsed.scheme.casefold() not in HTTP_SCHEMES:
        return LinkRecord(href, resolved, "non_http")

    # Remove fragment for a cleaner URL record.
    if parsed.scheme or parsed.netloc:
        parsed = parsed._replace(fragment="")
        resolved = urlunparse(parsed)

    if not page_url:
        if not parsed.netloc:
            return LinkRecord(href, resolved, "relative")
        return LinkRecord(href, resolved, "unknown_host")

    page_host = (urlparse(page_url).hostname or "").casefold()
    link_host = (urlparse(resolved).hostname or "").casefold()

    if not link_host or link_host == page_host:
        return LinkRecord(href, resolved, "internal")
    return LinkRecord(href, resolved, "external")


def extract_internal_links(
    html: str,
    page_url: str,
) -> dict:
    cleaned_page_url = _normalize_http_url(page_url)
    if not cleaned_page_url:
        raise ValueError("page_url is required for internal-link classification.")

    snapshot = parse_html(html)
    records = [
        _classify_link(href, cleaned_page_url)
        for href in snapshot.links
    ]

    internal = []
    seen = set()
    for record in records:
        if record.kind == "internal" and record.resolved not in seen:
            seen.add(record.resolved)
            internal.append(record.resolved)

    return {
        "page_url": cleaned_page_url,
        "raw_link_count": len(snapshot.links),
        "internal_link_count": len(internal),
        "internal_links": internal,
        "classification_counts": {
            kind: sum(record.kind == kind for record in records)
            for kind in sorted({record.kind for record in records})
        },
        "links": [
            {
                "original": record.original,
                "resolved": record.resolved,
                "kind": record.kind,
            }
            for record in records
        ],
    }


def _directives(values: list[str]) -> list[str]:
    found: set[str] = set()
    for value in values:
        for token in re.split(r"[\s,;]+", value.casefold()):
            token = token.strip()
            if token:
                found.add(token)
    return sorted(found)


def check_robots_meta(html: str) -> dict:
    snapshot = parse_html(html)
    robots = _directives(snapshot.robots_values)
    googlebot = _directives(snapshot.googlebot_values)
    combined = sorted(set(robots) | set(googlebot))

    return {
        "robots_values": snapshot.robots_values,
        "googlebot_values": snapshot.googlebot_values,
        "robots_directives": robots,
        "googlebot_directives": googlebot,
        "effective_detected_directives": combined,
        "noindex_detected": "noindex" in combined,
        "nofollow_detected": "nofollow" in combined,
        "issues": [
            {
                "code": "noindex_detected",
                "severity": "warning",
                "message": (
                    "A noindex directive was detected in robots/googlebot meta. "
                    "Confirm that this is intentional."
                ),
            }
        ] if "noindex" in combined else [],
        "note": (
            "This checks HTML meta directives only. HTTP X-Robots-Tag headers "
            "are outside the scope of an HTML snapshot."
        ),
    }


def audit_page(
    html: str,
    page_url: str = "",
    primary_keyword: str = "",
) -> dict:
    title = get_page_title(html, primary_keyword)
    meta = get_meta_description(html, primary_keyword)
    headings = extract_headings(html, primary_keyword)
    canonical = get_canonical(html, page_url)
    robots = check_robots_meta(html)

    internal_links = (
        extract_internal_links(html, page_url)
        if page_url.strip()
        else {
            "page_url": None,
            "raw_link_count": len(parse_html(html).links),
            "internal_link_count": None,
            "internal_links": [],
            "classification_counts": {},
            "links": [],
            "note": "Provide page_url to classify internal vs external links.",
        }
    )

    issues = (
        title["issues"]
        + meta["issues"]
        + headings["issues"]
        + canonical["issues"]
        + robots["issues"]
    )

    counts = {
        severity: sum(issue["severity"] == severity for issue in issues)
        for severity in ("error", "warning", "info")
    }

    return {
        "page_url": _clean_text(page_url) or None,
        "primary_keyword": _clean_text(primary_keyword) or None,
        "title": title,
        "meta_description": meta,
        "headings": headings,
        "canonical": canonical,
        "robots": robots,
        "internal_links": internal_links,
        "summary": {
            "issue_counts": counts,
            "issues": issues,
        },
        "trust_boundary": (
            "HTML was parsed as untrusted data. This tool made no network "
            "request and executed no page script."
        ),
    }


def load_guidelines() -> dict:
    path = Path(__file__).resolve().parent / "resources" / "on_page_guidelines.json"
    return json.loads(path.read_text(encoding="utf-8"))
