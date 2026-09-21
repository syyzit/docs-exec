"""Extraction unit tests."""

from docs_exec.extract import extract_blocks_from_text


def test_extracts_bash_sh_shell_only():
    text = (
        "# t\n\n"
        "```bash\necho hi\n```\n\n"
        "```sh\necho sh\n```\n\n"
        "```shell\necho shell\n```\n\n"
        "```python\nprint('nope')\n```\n"
    )
    blocks = extract_blocks_from_text(text, filename="t.md")
    assert [(b.lang, b.index) for b in blocks] == [
        ("bash", 1),
        ("sh", 2),
        ("shell", 3),
    ]


def test_skip_via_info_string():
    text = "```bash skip-docs-exec\nexit 99\n```\n"
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.skipped is True


def test_skip_via_docs_exec_skip_token():
    text = "```bash docs-exec:skip\nexit 99\n```\n"
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.skipped is True


def test_skip_via_html_comment():
    text = "<!-- docs-exec:skip -->\n\n```bash\nexit 99\n```\n"
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.skipped is True


def test_non_adjacent_comment_does_not_skip():
    text = (
        "<!-- docs-exec:skip -->\n\nsome text\n\nmore text\n\n"
        "even more\n\n```bash\necho hi\n```\n"
    )
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.skipped is False


def test_line_numbers_and_code():
    text = "# t\n\n```bash\necho a\necho b\n```\n"
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.line == 3
    assert block.code == "echo a\necho b\n"


def test_nested_fences_inside_markdown_block_are_ignored():
    text = "````markdown\n```bash\necho hi\n```\n````\n"
    assert extract_blocks_from_text(text, filename="t.md") == []


def test_tilde_fences_supported():
    text = "~~~bash\necho hi\n~~~\n"
    (block,) = extract_blocks_from_text(text, filename="t.md")
    assert block.lang == "bash"
    assert block.code == "echo hi\n"
