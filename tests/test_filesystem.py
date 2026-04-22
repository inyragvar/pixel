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
