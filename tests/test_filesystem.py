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
