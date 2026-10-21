import tempfile
import unittest
from pathlib import Path

from evidence.leaks.check import LEAKS, Leak, check, locate

TOY = Leak("toy", "why", (("a.py", ("first()", "second()")),))


class CheckTests(unittest.TestCase):
    def test_locate_requires_fragments_in_order(self):
        self.assertEqual(locate("x\nfirst()\ny\nsecond()\n", ("first()", "second()")), [2, 4])
        self.assertIsNone(locate("second()\nfirst()\n", ("first()", "second()")))
        self.assertIsNone(locate("first()\n", ("first()", "second()")))

    def test_leak_found_only_when_its_code_is_present(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(check(TOY, root))
            (root / "a.py").write_text("first()\nsecond()\n", encoding="utf-8")
            self.assertEqual(check(TOY, root), {"a.py": [1, 2]})
            (root / "b.py").write_text("first()\n", encoding="utf-8")
            self.assertIsNone(check(TOY, root, {"a.py": "b.py"}))

    def test_every_leak_cites_code(self):
        self.assertEqual(len(LEAKS), 6)
        self.assertTrue(all(leak.code and all(fragments for _, fragments in leak.code) for leak in LEAKS))


if __name__ == "__main__":
    unittest.main()
