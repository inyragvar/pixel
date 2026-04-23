from pathlib import Path

from agent.tools.filesystem import FileSystemTool


def test_filesystem_read_write_roundtrip(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    tool.write_file("src/example.py", "print('hi')\n")
    content = tool.read_file("src/example.py")
    assert content == "print('hi')\n"


def test_filesystem_prevents_escape(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    try:
        tool.write_file("../escape.txt", "nope")
    except ValueError as exc:
        assert "escapes workspace" in str(exc)
    else:
        raise AssertionError("Expected path escape protection")


def test_replace_and_append(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    tool.write_file("notes.txt", "hello\n")
    tool.append_file("notes.txt", "world\n")
    tool.replace_in_file("notes.txt", "world", "agent")
    assert tool.read_file("notes.txt") == "hello\nagent\n"


def test_apply_patch_and_rollback(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    changed = tool.apply_patch(
        """--- a/main.py
+++ b/main.py
@@ -1 +1 @@
-print('hello')
+print('hello world')
"""
    )
    assert changed == ["main.py"]
    assert tool.read_file("main.py") == "print('hello world')\n"
    assert tool.tracked_changes() == ["main.py"]

    rolled_back = tool.rollback_file("main.py")
    assert rolled_back == "main.py"
    assert tool.read_file("main.py") == "print('hello')\n"
    assert tool.tracked_changes() == []


def test_rollback_all_restores_created_file(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    tool.write_file("created.txt", "new\n")
    assert (tmp_path / "created.txt").exists()
    assert tool.tracked_changes() == ["created.txt"]
    changed = tool.rollback_all()
    assert changed == ["created.txt"]
    assert not (tmp_path / "created.txt").exists()


def test_denylist_blocks_edit_path(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path, denylist_patterns=["secrets/**"])
    try:
        tool.write_file("secrets/api.txt", "token")
    except ValueError as exc:
        assert "denylist" in str(exc)
    else:
        raise AssertionError("Expected denylist protection")


def test_allowlist_blocks_non_matching_path(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path, allowlist_patterns=["src/**/*.py", "README.md"])
    try:
        tool.write_file("notes.txt", "hello")
    except ValueError as exc:
        assert "allowlist" in str(exc)
    else:
        raise AssertionError("Expected allowlist protection")


def test_binary_file_read_is_blocked(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path)
    (tmp_path / "binary.txt").write_bytes(b"text\x00binary")
    try:
        tool.read_file("binary.txt")
    except ValueError as exc:
        assert "Binary file operations are blocked" in str(exc)
    else:
        raise AssertionError("Expected binary file blocking")


def test_list_files_filters_binary_and_denied_paths(tmp_path: Path) -> None:
    tool = FileSystemTool(tmp_path, denylist_patterns=["private/**"])
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "private").mkdir()
    (tmp_path / "private" / "secret.txt").write_text("secret\n", encoding="utf-8")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00binary")
    assert tool.list_files() == ["src/main.py"]
