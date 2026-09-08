import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.review_v2 import preserve


class PreservationTests(unittest.TestCase):
    def test_isolated_restore_preserves_bytes_and_blocks_incomplete_cutover(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            repository = root / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            registry = repository / "data/registry/papers.csv"
            registry.parent.mkdir(parents=True)
            original = b"id,title\r\nTEST-1,Synthetic publication\r\n"
            registry.write_bytes(original)
            subprocess.run(["git", "add", "."], cwd=repository, check=True)
            subprocess.run(["git", "-c", "user.name=Preservation fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "Synthetic snapshot fixture"], cwd=repository, check=True)
            backup, restored = root / "backup", root / "restored"
            with patch.object(preserve, "ROOT", repository):
                manifest = preserve.snapshot(backup)
            self.assertFalse(manifest["cutover_ready"])
            self.assertTrue(manifest["history_complete"])
            self.assertEqual(manifest["counts"]["data/registry/papers.csv"], 1)
            self.assertEqual(preserve.restore(backup, restored)["verified_files"], 1)
            self.assertEqual((restored / "data/registry/papers.csv").read_bytes(), original)
            self.assertEqual(registry.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, "new isolated directory"):
                preserve.restore(backup, restored)
            manifest["cutover_ready"] = True
            (backup / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "readiness mismatch"):
                preserve.verify(backup)
            manifest["cutover_ready"] = False
            (backup / "manifest.json").write_text(json.dumps(manifest))
            with (backup / "repository.tar").open("ab") as handle:
                handle.write(b"TAMPERED")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                preserve.verify(backup)


if __name__ == "__main__":
    unittest.main()
