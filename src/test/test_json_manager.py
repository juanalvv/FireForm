import sys
import os
import pytest

# Allow tests to import from src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from json_manager import JsonManager


def test_load_json_corrupted_file_raises_ioerror(tmp_path):
    """
    This test ensures that a malformed JSON file
    raises an IOError instead of crashing with JSONDecodeError.
    """

    # Create a temporary corrupted JSON file
    corrupted_file = tmp_path / "bad.json"
    corrupted_file.write_text("{ invalid }")

    manager = JsonManager()

    # We expect an IOError to be raised
    with pytest.raises(IOError):
        manager.load_json(str(corrupted_file))
    
def test_load_json_valid_file(tmp_path):
    """
    This test ensures a valid JSON file
    is correctly loaded and returned.
    """

    valid_file = tmp_path / "good.json"
    valid_file.write_text('{"name": "John", "age": 30}')

    manager = JsonManager()
    result = manager.load_json(str(valid_file))

    assert result == {"name": "John", "age": 30}

def test_load_json_missing_file_returns_empty_list(tmp_path):
    """
    This test ensures that when a file does not exist,
    an empty list is returned.
    """

    missing_file = tmp_path / "does_not_exist.json"

    manager = JsonManager()
    result = manager.load_json(str(missing_file))

    assert result == []