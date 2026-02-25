import unittest
from pathlib import Path
from input_manager import InputManager
from json_manager import JsonManager
from backend import textToJSON


class TestInputManagerIntegration(unittest.TestCase):
    """Test InputManager file reading functionality"""

    def setUp(self):
        self.manager = InputManager()
        self.test_dir = Path(__file__).resolve().parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        # Clean up test files
        for file in self.test_dir.glob("*.txt"):
            file.unlink()

    def test_read_valid_transcript_file(self):
        """Test reading a valid transcript file"""
        test_file = self.test_dir / "transcript.txt"
        test_content = "My name is John Doe and my phone is 555-1234"
        test_file.write_text(test_content, encoding="utf-8")

        result = self.manager.file_to_text(str(test_file))
        self.assertEqual(result, test_content)

    def test_read_empty_file(self):
        """Test reading an empty file"""
        test_file = self.test_dir / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        result = self.manager.file_to_text(str(test_file))
        self.assertEqual(result, "")

    def test_file_not_found(self):
        """Test handling of non-existent file"""
        with self.assertRaises(FileNotFoundError):
            self.manager.file_to_text(str(self.test_dir / "nonexistent.txt"))


class TestJsonManagerIntegration(unittest.TestCase):
    """Test JsonManager save and load functionality"""

    def setUp(self):
        self.manager = JsonManager()
        self.test_dir = Path(__file__).resolve().parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        # Clean up test files
        for file in self.test_dir.glob("*.json"):
            file.unlink()

    def test_save_and_load_json(self):
        """Test saving and loading JSON data"""
        test_file = self.test_dir / "output.json"
        test_data = {
            "name": "John Doe",
            "phone": "555-1234",
            "email": "john@example.com",
        }

        self.manager.save_json(test_data, str(test_file))
        loaded_data = self.manager.load_json(str(test_file))

        self.assertEqual(loaded_data, test_data)

    def test_save_empty_dict(self):
        """Test saving an empty dictionary"""
        test_file = self.test_dir / "empty_output.json"
        test_data = {}

        self.manager.save_json(test_data, str(test_file))
        loaded_data = self.manager.load_json(str(test_file))

        self.assertEqual(loaded_data, test_data)

    def test_load_nonexistent_file(self):
        """Test loading a non-existent file returns empty list"""
        result = self.manager.load_json(
            str(self.test_dir / "nonexistent.json")
        )
        self.assertEqual(result, [])

    def test_load_corrupted_json(self):
        """Test loading corrupted JSON file raises IOError"""
        test_file = self.test_dir / "corrupted.json"
        test_file.write_text("{invalid json content}", encoding="utf-8")

        with self.assertRaises(IOError):
            self.manager.load_json(str(test_file))


class TestTextToJSONIntegration(unittest.TestCase):
    """Test textToJSON with InputManager and JsonManager"""

    def setUp(self):
        self.input_manager = InputManager()
        self.json_manager = JsonManager()
        self.test_dir = Path(__file__).resolve().parent / "test_data"
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        for file in self.test_dir.glob("*"):
            if file.is_file():
                file.unlink()

    def test_full_workflow(self):
        """Test complete workflow: read transcript → extract data → save JSON"""
        # Create test transcript
        transcript_file = self.test_dir / "transcript.txt"
        transcript = "My name is John Doe. My phone number is 555-1234. My email is john@example.com"
        transcript_file.write_text(transcript, encoding="utf-8")

        # Read transcript
        user_input = self.input_manager.file_to_text(str(transcript_file))
        self.assertEqual(user_input, transcript)

        # Extract data (with defined fields)
        definitions = ["name", "phone", "email"]
        t2j = textToJSON(user_input, definitions)
        extracted_data = t2j.get_data()

        # Verify extraction returned a dictionary
        self.assertIsInstance(extracted_data, dict)

        # Save extracted data
        output_file = self.test_dir / "extracted.json"
        self.json_manager.save_json(extracted_data, str(output_file))

        # Verify file was created and can be loaded
        loaded_data = self.json_manager.load_json(str(output_file))
        self.assertEqual(loaded_data, extracted_data)


if __name__ == "__main__":
    unittest.main()
