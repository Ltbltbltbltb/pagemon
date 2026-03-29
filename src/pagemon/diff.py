"""Content diffing engine for pagemon."""

from __future__ import annotations

import difflib
import re


def clean_content(html: str, selector: str | None = None) -> str:
    """Extract and clean text content from HTML.

    If a CSS selector is provided, only content matching that selector is extracted.
    Otherwise, the full body text is used.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return _strip_tags(html)

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    if selector:
        elements = soup.select(selector)
        if not elements:
            return ""
        text_parts = [el.get_text(separator="\n", strip=True) for el in elements]
        return "\n\n".join(text_parts)

    body = soup.find("body") or soup
    return body.get_text(separator="\n", strip=True)


def compute_diff(old_content: str, new_content: str) -> str:
    """Compute a unified diff between old and new content."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="previous",
        tofile="current",
        lineterm="",
    )
    return "".join(diff)


def has_meaningful_change(old_content: str, new_content: str) -> bool:
    """Check if the content change is meaningful (not just whitespace/timestamp noise)."""
    old_normalized = _normalize(old_content)
    new_normalized = _normalize(new_content)
    return old_normalized != new_normalized


def _normalize(text: str) -> str:
    """Normalize text by removing common noise patterns."""
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove common timestamp patterns
    text = re.sub(r"\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)?", "", text)
    # Remove common date patterns
    text = re.sub(r"\d{1,2}/\d{1,2}/\d{2,4}", "", text)
    return text


def _strip_tags(html: str) -> str:
    """Fallback tag stripper when BeautifulSoup is not available."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
