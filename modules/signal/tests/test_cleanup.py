import json
import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_legacy import cleanup


class CleanupTests(unittest.TestCase):
    def test_explicit_cleanup_preserves_active_artifacts_and_records_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "data/processed/disentanglement/sampling_design_audit_v1"
            legacy.mkdir(parents=True)
            (legacy / "old.csv").write_text("old", encoding="utf-8")
            active = root / "data/processed/disentanglement/sampling_design_audit_v3"
            active.mkdir(parents=True)
            (active / "manifest.json").write_text("{}", encoding="utf-8")
            plan = cleanup(root)
            self.assertEqual(len(plan["targets"]), 1)
            self.assertTrue(legacy.exists())
            report = root / "cleanup.json"
            result = cleanup(root, apply=True, report=report)
            self.assertFalse(legacy.exists())
            self.assertTrue((active / "manifest.json").exists())
            self.assertTrue(result["preserved_manifests_unchanged"])
            self.assertEqual(json.loads(report.read_text())["total_bytes"], 3)
            self.assertEqual(len(result["targets"][0]["files"][0]["sha256"]), 64)
            with self.assertRaises(FileExistsError):
                cleanup(root, apply=True, report=report)

    def test_referenced_outputs_and_remaining_source_code_block_deletion(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy = root / "data/processed/disentanglement/sampling_design_audit_v1"
            legacy.mkdir(parents=True)
            active = root / "data/processed/disentanglement/sampling_design_audit_v3"
            active.mkdir(parents=True)
            manifest = active / "manifest.json"
            manifest.write_text(json.dumps({"input": str(legacy / "data.csv")}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "references"):
                cleanup(root)
            manifest.write_text("{}", encoding="utf-8")
            code = root / "discord_disentanglement/approaches"
            code.mkdir(parents=True)
            (code / "important.py").write_text("value = 1", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-cache"):
                cleanup(root)