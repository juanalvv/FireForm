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