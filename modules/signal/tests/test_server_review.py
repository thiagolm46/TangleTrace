import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from discord_data.extraction import load_selected_servers
from discord_filtering.cli import main
from discord_filtering.server_review import apply_server_review, prioritize_servers
from discord_filtering.storage import OutputExistsError, sha256_file


ROOT = Path(__file__).resolve().parents[1]


class ServerReviewTests(unittest.TestCase):
    def test_positive_only_linear_quartiles_strict_fence_and_review(self):
        scores = [0, -5, *([1] * 5), *([2] * 5), 3.5, 20]
        rows = [
            {"guild_id": str(index), "name": f"Server {index}", "software_affinity_score": score}
            for index, score in enumerate(scores)
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "scores.parquet"
            candidates = root / "candidates.parquet"
            selected = root / "selected.parquet"
            pd.DataFrame(rows).to_parquet(source, index=False)
            original_hash = sha256_file(source)
            _, manifest_path = prioritize_servers(source, candidates)
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["statistics"], {"q1": 1, "q3": 2, "upper_fence": 3.5})
            self.assertEqual(manifest["counts"]["positive_servers"], 12)
            self.assertEqual(pd.read_parquet(candidates).guild_id.tolist(), ["13"])
            self.assertEqual(manifest["inputs"][0]["sha256"], original_hash)
            self.assertEqual(manifest["output"]["sha256"], sha256_file(candidates))
            review = root / "review.csv"
            review.write_text("guild_id,decision\n13,accept\n", encoding="utf-8")
            _, selected_manifest = apply_server_review(candidates, review, selected)
            lookup, ids = load_selected_servers(selected)
            self.assertEqual(ids, {"13"})
            self.assertEqual(lookup["13"]["name"], "Server 13")
            self.assertEqual(pd.read_parquet(selected).manual_decision.tolist(), ["accept"])
            self.assertEqual(json.loads(selected_manifest.read_text())["counts"]["selected_servers"], 1)
            self.assertEqual(sha256_file(source), original_hash)
            with self.assertRaises(OutputExistsError):
                prioritize_servers(source, candidates)
            with self.assertRaises(OutputExistsError):
                apply_server_review(candidates, review, selected)

    def test_review_requires_exact_unique_ids_and_explicit_decisions(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "queue.json"
            source.write_text(json.dumps([{"guild_id": "1"}, {"guild_id": "2"}]))
            cases = (
                ("guild_id,decision\n1,accept\n", "exactly"),
                ("guild_id,decision\n1,accept\n2,reject\n3,accept\n", "exactly"),
                ("guild_id,decision\n1,accept\n1,reject\n", "duplicate"),
                ("guild_id,decision\n1,accept\n2,yes\n", "invalid decision"),
                ("guild_id,decision\n1,reject\n2,reject\n", "accepts no servers"),
            )
            for content, error in cases:
                review = root / "review.csv"
                review.write_text(content)
                with self.subTest(content=content), self.assertRaisesRegex(ValueError, error):
                    apply_server_review(source, review, root / "selected.parquet")
                self.assertFalse((root / "selected.parquet").exists())

    def test_rejections_are_not_materialized(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, review, output = (root / name for name in ("queue.json", "review.csv", "selected.parquet"))
            source.write_text(json.dumps([{"guild_id": "1", "name": "Accepted"}, {"guild_id": "2", "name": "Rejected"}]))
            review.write_text("guild_id,decision\n1,accept\n2,reject\n")
            apply_server_review(source, review, output)
            self.assertEqual(load_selected_servers(output)[1], {"1"})

    def test_invalid_scores_and_ids_fail_without_output(self):
        cases = (
            ([{"guild_id": "1", "software_affinity_score": 0}], "positive"),
            ([{"guild_id": "1", "software_affinity_score": float("inf")}], "finite"),
            ([{"guild_id": "1", "software_affinity_score": True}], "finite"),
            ([{"guild_id": "1"}], "finite"),
            ([{"guild_id": " 1", "software_affinity_score": 1}], "canonical"),
            ([{"guild_id": "1"}, {"guild_id": "1"}], "duplicate"),
            ([], "empty"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, output = root / "source.json", root / "queue.parquet"
            for rows, error in cases:
                source.write_text(json.dumps(rows))
                with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, error):
                    prioritize_servers(source, output)
                self.assertFalse(output.exists())

    def test_cli_wires_review_commands_and_reports_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, queue, review, output = (root / name for name in ("scores.json", "queue.parquet", "review.csv", "selected.parquet"))
            rows = [{"guild_id": str(index), "software_affinity_score": value} for index, value in enumerate([1] * 10 + [20])]
            source.write_text(json.dumps(rows))
            review.write_text("guild_id,decision\n10,accept\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["prioritize-servers", "--input", str(source), "--output", str(queue)]), 0)
                self.assertEqual(main(["apply-server-review", "--input", str(queue), "--review", str(review), "--output", str(output)]), 0)
            with contextlib.redirect_stderr(io.StringIO()) as errors:
                self.assertEqual(main(["apply-server-review", "--input", str(queue), "--review", str(review), "--output", str(output)]), 2)
            self.assertIn("error:", errors.getvalue())

    def test_versioned_historical_decisions_and_default_exclusion_file(self):
        from discord_filtering.channel_selection import DEFAULT_EXCLUSIONS

        review = pd.read_csv(ROOT / "configs/filtering/server_review.v1.csv", dtype=str)
        self.assertEqual(len(review), 37)
        self.assertFalse(review.guild_id.duplicated().any())
        self.assertEqual(review.decision.value_counts().to_dict(), {"accept": 31, "reject": 6})
        self.assertEqual(review.loc[review.guild_id.eq("135844298527735818"), "decision"].item(), "reject")
        self.assertEqual(DEFAULT_EXCLUSIONS, ROOT / "configs/filtering/channel_exclusions.v1.txt")
        self.assertTrue(DEFAULT_EXCLUSIONS.is_file())
