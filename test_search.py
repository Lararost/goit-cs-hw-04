"""Перевірка обох реальних реалізацій, включно зі spawn-процесами."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from threading_search import search_threading
from multiprocessing_search import search_multiprocessing


class SearchTests(unittest.TestCase):
    def test_matches_and_file_errors(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            a, b, empty, binary = [root / n for n in ("a.txt", "b.txt", "empty.txt", "bad.txt")]
            a.write_text("PYTHON python\nПАРАЛЕЛІЗМ\nміж\nрядками", encoding="utf-8")
            b.write_text("Docker and python", encoding="utf-8-sig")
            empty.write_text("", encoding="utf-8")
            binary.write_bytes(b"\xff\xff")
            missing = root / "missing.txt"
            files = [a, b, empty, binary, missing, root, a]
            words = ["python", "паралелізм", "docker", "absent", "між\nрядками", "python"]
            expected = {"python": sorted([str(a), str(b)]), "паралелізм": [str(a)],
                        "docker": [str(b)], "absent": [], "між\nрядками": [str(a)]}
            for search in (search_threading, search_multiprocessing):
                for workers in (1, 3, 20):
                    with self.subTest(search=search.__name__, workers=workers):
                        errors = StringIO()
                        with redirect_stderr(errors):
                            self.assertEqual(search(files, words, workers), expected)
                        self.assertIn("UnicodeDecodeError", errors.getvalue())
                        self.assertIn("FileNotFoundError", errors.getvalue())
                        self.assertIn("IsADirectoryError", errors.getvalue())

    def test_empty_and_invalid(self):
        for search in (search_threading, search_multiprocessing):
            self.assertEqual(search([], ["word"], 4), {"word": []})
            for workers in (0, -1, True):
                with self.assertRaises(ValueError):
                    search([], ["word"], workers)
            for keywords in ([], [""], ["   "]):
                with self.assertRaises(ValueError):
                    search([], keywords)

    def test_large_queue_response(self):
        # Достатньо великий Queue payload: перевірка читання до join.
        with TemporaryDirectory() as directory:
            p = Path(directory) / "large.txt"
            words = [f"term{i:04}" for i in range(2000)]
            p.write_text(" ".join(words), encoding="utf-8")
            self.assertEqual(search_multiprocessing([p], words, 2),
                             {word: [str(p)] for word in words})


if __name__ == "__main__":
    unittest.main()
