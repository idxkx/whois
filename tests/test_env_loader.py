import os
import tempfile
import unittest
from pathlib import Path

from server.app import load_env_file


class EnvLoaderTest(unittest.TestCase):
    def test_load_env_file_sets_defaults(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "# comment\nDOMAIN_QUERY_PORT=9100\nDOMAIN_QUERY_HOST='0.0.0.0'\nUNKNOWN=value with spaces\n"
            )

        os.environ.pop("DOMAIN_QUERY_PORT", None)
        os.environ["UNKNOWN"] = "keep"

        values = load_env_file(Path(path))
        self.assertEqual(values["DOMAIN_QUERY_PORT"], "9100")
        self.assertEqual(os.environ["DOMAIN_QUERY_PORT"], "9100")
        # 不覆盖已有环境变量
        self.assertEqual(os.environ["UNKNOWN"], "keep")


if __name__ == "__main__":
    unittest.main()
