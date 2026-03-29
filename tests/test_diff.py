"""Tests for pagemon.diff: clean_content, compute_diff, has_meaningful_change."""

from __future__ import annotations

from pagemon.diff import (
    _normalize,
    _strip_tags,
    clean_content,
    compute_diff,
    has_meaningful_change,
)

# ---------------------------------------------------------------------------
# clean_content
# ---------------------------------------------------------------------------


class TestCleanContent:
    def test_should_remove_script_tags(self) -> None:
        html = "<html><body><p>Hello</p><script>alert('x')</script></body></html>"
        result = clean_content(html)
        assert "alert" not in result

    def test_should_remove_style_tags(self) -> None:
        html = "<html><body><p>Hello</p><style>.x{color:red}</style></body></html>"
        result = clean_content(html)
        assert "color" not in result

    def test_should_remove_nav_tags(self) -> None:
        html = "<html><body><nav>Menu items</nav><main>Content</main></body></html>"
        result = clean_content(html)
        assert "Menu items" not in result

    def test_should_remove_footer_tags(self) -> None:
        html = "<html><body><main>Content</main><footer>Footer junk</footer></body></html>"
        result = clean_content(html)
        assert "Footer junk" not in result

    def test_should_remove_header_tags(self) -> None:
        html = "<html><body><header>Top nav</header><main>Content</main></body></html>"
        result = clean_content(html)
        assert "Top nav" not in result

    def test_should_extract_body_text(self) -> None:
        html = "<html><body><p>Main content here</p></body></html>"
        result = clean_content(html)
        assert "Main content here" in result

    def test_should_return_empty_string_when_selector_matches_nothing(self) -> None:
        html = "<html><body><p>Hello</p></body></html>"
        result = clean_content(html, selector=".nonexistent")
        assert result == ""

    def test_should_extract_only_selected_element(self) -> None:
        html = "<html><body><div class='price'>$99</div><div class='noise'>junk</div></body></html>"
        result = clean_content(html, selector=".price")
        assert "$99" in result
        assert "junk" not in result

    def test_should_handle_empty_html(self) -> None:
        result = clean_content("")
        assert isinstance(result, str)

    def test_should_handle_html_without_body_tag(self) -> None:
        html = "<p>Content without body tag</p>"
        result = clean_content(html)
        assert "Content without body tag" in result

    def test_should_extract_multiple_selector_matches(self) -> None:
        html = "<html><body><p class='item'>First</p><p class='item'>Second</p></body></html>"
        result = clean_content(html, selector=".item")
        assert "First" in result
        assert "Second" in result

    def test_should_strip_noscript_tags(self) -> None:
        html = "<html><body><noscript>Enable JS</noscript><p>Real content</p></body></html>"
        result = clean_content(html)
        assert "Enable JS" not in result


# ---------------------------------------------------------------------------
# compute_diff
# ---------------------------------------------------------------------------


class TestComputeDiff:
    def test_should_return_empty_string_when_content_identical(self) -> None:
        result = compute_diff("same content", "same content")
        assert result == ""

    def test_should_include_removed_line_marker(self) -> None:
        result = compute_diff("old line\n", "new line\n")
        assert "-old line" in result

    def test_should_include_added_line_marker(self) -> None:
        result = compute_diff("old line\n", "new line\n")
        assert "+new line" in result

    def test_should_use_previous_as_fromfile_label(self) -> None:
        result = compute_diff("a\n", "b\n")
        assert "--- previous" in result

    def test_should_use_current_as_tofile_label(self) -> None:
        result = compute_diff("a\n", "b\n")
        assert "+++ current" in result

    def test_should_handle_empty_old_content(self) -> None:
        result = compute_diff("", "new content\n")
        assert "+new content" in result

    def test_should_handle_empty_new_content(self) -> None:
        result = compute_diff("old content\n", "")
        assert "-old content" in result

    def test_should_handle_both_empty_contents(self) -> None:
        result = compute_diff("", "")
        assert result == ""

    def test_should_include_context_lines_around_changes(self) -> None:
        old = "line1\nline2\nline3\nline4\nline5\n"
        new = "line1\nline2\nchanged\nline4\nline5\n"
        result = compute_diff(old, new)
        assert "line1" in result or "line5" in result

    def test_should_return_string(self) -> None:
        result = compute_diff("a", "b")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# has_meaningful_change
# ---------------------------------------------------------------------------


class TestHasMeaningfulChange:
    def test_should_return_false_when_content_identical(self) -> None:
        result = has_meaningful_change("hello world", "hello world")
        assert result is False

    def test_should_return_true_when_content_differs(self) -> None:
        result = has_meaningful_change("old content", "new content")
        assert result is True

    def test_should_return_false_when_only_whitespace_differs(self) -> None:
        result = has_meaningful_change("hello   world", "hello world")
        assert result is False

    def test_should_return_false_when_only_time_differs(self) -> None:
        result = has_meaningful_change("Updated at 10:30 AM", "Updated at 11:45 PM")
        assert result is False

    def test_should_return_false_when_only_date_differs(self) -> None:
        result = has_meaningful_change("Published 1/1/2024", "Published 12/31/2024")
        assert result is False

    def test_should_return_true_when_price_changes(self) -> None:
        result = has_meaningful_change("Price: $10.00", "Price: $12.50")
        assert result is True

    def test_should_return_true_when_headline_changes(self) -> None:
        result = has_meaningful_change(
            "Breaking: Market closes up",
            "Breaking: Market closes down",
        )
        assert result is True

    def test_should_handle_empty_strings(self) -> None:
        result = has_meaningful_change("", "")
        assert result is False

    def test_should_return_true_when_one_is_empty(self) -> None:
        result = has_meaningful_change("some content", "")
        assert result is True


# ---------------------------------------------------------------------------
# _normalize (internal, tested for coverage)
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_should_collapse_multiple_spaces(self) -> None:
        result = _normalize("hello   world")
        assert result == "hello world"

    def test_should_strip_leading_trailing_whitespace(self) -> None:
        result = _normalize("  hello  ")
        assert result == "hello"

    def test_should_remove_hh_mm_time_pattern(self) -> None:
        result = _normalize("at 10:30 today")
        assert "10:30" not in result

    def test_should_remove_time_with_seconds(self) -> None:
        result = _normalize("at 10:30:45 today")
        assert "10:30:45" not in result

    def test_should_remove_am_pm_suffix(self) -> None:
        result = _normalize("10:00 AM meeting")
        assert "AM" not in result

    def test_should_remove_date_pattern(self) -> None:
        result = _normalize("on 12/25/2024 holiday")
        assert "12/25/2024" not in result

    def test_should_normalize_newlines_as_whitespace(self) -> None:
        result = _normalize("line1\nline2")
        assert result == "line1 line2"


# ---------------------------------------------------------------------------
# _strip_tags (fallback, tested for coverage)
# ---------------------------------------------------------------------------


class TestStripTags:
    def test_should_remove_html_tags(self) -> None:
        result = _strip_tags("<p>Hello</p>")
        assert "<p>" not in result
        assert "Hello" in result

    def test_should_remove_script_content(self) -> None:
        result = _strip_tags("<script>alert('x')</script><p>real</p>")
        assert "alert" not in result

    def test_should_remove_style_content(self) -> None:
        result = _strip_tags("<style>.x{color:red}</style><p>real</p>")
        assert "color" not in result

    def test_should_handle_empty_string(self) -> None:
        result = _strip_tags("")
        assert result == ""

    def test_should_collapse_extra_whitespace(self) -> None:
        result = _strip_tags("<p>hello   world</p>")
        assert "hello world" in result
