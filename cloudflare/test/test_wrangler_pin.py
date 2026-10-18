"""wrangler の版を lockfile にそろえる（scripts/wrangler_pin.py、issue #131）。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import wrangler_pin as WP  # noqa: E402


class WranglerPinTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.lock = self.root / "package-lock.json"
        self.lock.write_text(json.dumps({"packages": {"node_modules/wrangler": {"version": "4.99.1"}}}), encoding="utf-8")

    def install(self, version):
        p = self.root / "node_modules" / "wrangler"
        p.mkdir(parents=True, exist_ok=True)
        (p / "package.json").write_text(json.dumps({"version": version}), encoding="utf-8")

    def test_the_repository_lockfile_names_an_exact_wrangler(self):
        self.assertRegex(WP.locked_version(), r"^4\.\d+\.\d+$")

    def test_without_an_install_npx_fetches_the_locked_version_by_name(self):
        self.assertEqual(WP.wrangler_cmd("npx", self.root, self.lock), ["npx", "--yes", "wrangler@4.99.1"])

    def test_an_install_of_the_locked_version_is_used_without_fetching(self):
        self.install("4.99.1")
        self.assertEqual(WP.wrangler_cmd("npx", self.root, self.lock), ["npx", "--no-install", "wrangler"])

    def test_an_install_of_another_version_is_not_used(self):
        self.install("4.100.0")
        self.assertEqual(WP.wrangler_cmd("npx", self.root, self.lock), ["npx", "--yes", "wrangler@4.99.1"])

    def test_no_floating_wrangler_is_left_in_the_tools(self):
        repo = HERE.parents[1]
        for f in [repo / "tools/admin/admin.py", repo / "cloudflare/scripts/backup_d1.py",
                  repo / "tools/taguri/deploy/github-actions/catalog.yml"]:
            self.assertNotIn("wrangler@4\"", f.read_text(encoding="utf-8"), f)
            self.assertNotIn("wrangler@4 ", f.read_text(encoding="utf-8"), f)


if __name__ == "__main__":
    unittest.main()
