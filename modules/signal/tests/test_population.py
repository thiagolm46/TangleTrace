import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from discord_disentanglement.population import characterize_population
from discord_disentanglement.population_report import (
    concentration_statistics,
    generate_population_report,
    markdown_table,
    number,
)


class PopulationTests(unittest.TestCase):
    def test_english_number_format_and_report_destinations(self):
        from discord_disentanglement.population_report import DEFAULT_REPORT as population_report
        from discord_disentanglement.sampling_audit import DEFAULT_REPORT as sampling_report

        self.assertEqual(number(11897859), "11,897,859")
        self.assertEqual(number(1234.5, 2), "1,234.50")
        self.assertEqual(number(None), "NA")
        root = Path(__file__).resolve().parents[1]
        for report in (population_report, sampling_report):
            self.assertTrue(report.is_relative_to(root / "data"))
            self.assertFalse(report.is_relative_to(root / "docs"))

    def test_quality_replies_concentration_and_distinct_authors(self):
        base = {
            "guild_id": "g", "guild_name": "Guild", "channel_id": "c",
            "channel_name": "general", "author_id": "a", "is_bot": False,
            "message_type": 0, "content": "hello", "attachment_count": 0,
            "embed_count": 0, "sticker_count": 0, "referenced_message_id": None,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        rows = [
            {**base, "message_id": "1"},
            {**base, "message_id": "2", "author_id": "b", "message_type": 19,
             "timestamp": "2026-01-01T00:01:00Z", "referenced_message_id": "1"},
            {**base, "message_id": "3", "is_bot": True},
            {**base, "message_id": "4", "content": "", "attachment_count": 1},
            {**base, "message_id": "5", "content": None},
            {**base, "message_id": "6", "timestamp": "bad"},
            {**base, "message_id": "7", "message_type": 19, "referenced_message_id": "absent"},
            {**base, "message_id": "8", "channel_id": "other"},
            {**base, "message_id": "9", "message_type": 19, "referenced_message_id": "8"},
            {**base, "message_id": "10", "message_type": 19, "referenced_message_id": "10"},
            {**base, "message_id": "duplicate"},
            {**base, "message_id": "duplicate"},
            {**base, "message_id": None, "is_bot": None},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "messages.parquet"
            output = Path(temporary) / "report"
            pd.DataFrame(rows).to_parquet(source, index=False)
            summary = characterize_population(source, output)
            self.assertEqual(summary["total_records"], 13)
            self.assertEqual(summary["distinct_human_authors"], 2)
            self.assertEqual(summary["usable_human_messages"], 10)
            self.assertEqual(summary["usable_records"], 12)
            self.assertEqual(summary["duplicate_id_records"], 2)
            self.assertEqual(summary["native_reply_records"], 4)
            self.assertEqual(summary["unusable_records"], 1)
            self.assertEqual(summary["human_messages_with_structural_issues"], 3)
            statuses = {row["status"]: row["replies"] for row in summary["reply_status_counts"]}
            self.assertEqual(statuses, {"resolved": 1, "parent_not_found": 1, "different_channel": 1, "not_preceding": 1})
            channels = pd.read_csv(output / "channels.csv")
            self.assertEqual(channels.loc[channels.channel_id == "c", "distinct_human_authors"].item(), 2)
            distances = pd.read_csv(output / "reply_distances.csv")
            resolved = distances.loc[distances.status == "resolved"].iloc[0]
            self.assertEqual(resolved["min_position_distance"], 7)
            self.assertEqual(json.loads(resolved["seconds_quantiles"])[1], 60)
            self.assertEqual(json.loads(resolved["usable_position_quantiles"])[1], 5)
            usable_concentration = next(item for item in summary["concentration_80_percent"] if item["scope"] == "channel" and item["population"] == "usable_human")
            self.assertEqual(usable_concentration["units_for_80_percent"], 1)
            with self.assertRaises(FileExistsError):
                characterize_population(source, output)
            report = Path(temporary) / "population.md"
            generate_population_report(output, report)
            text = report.read_text(encoding="utf-8")
            self.assertIn("| Total records | 13 |", text)
            self.assertIn("| Distinct human authors in the corpus | 2 |", text)
            self.assertIn("Complete channel inventory", text)
            self.assertIn("is not a global count", text)
            self.assertIn("nor averages quantiles", text)
            self.assertIn("| Unusable: no recorded text or media | 1 |", text)
            self.assertNotIn("Union of unusable records", text)
            before = report.read_bytes()
            generate_population_report(output, report, overwrite=True)
            self.assertEqual(report.read_bytes(), before)
            with self.assertRaises(FileExistsError):
                generate_population_report(output, report)
            (output / "channels.csv").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                generate_population_report(output, Path(temporary) / "tampered.md")

    def test_empty_population(self):
        from discord_data.extraction import MESSAGE_SCHEMA
        import pyarrow as pa
        import pyarrow.parquet as pq

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "empty.parquet"
            pq.write_table(pa.Table.from_batches([], schema=MESSAGE_SCHEMA), source)
            summary = characterize_population(source, Path(temporary) / "report")
            self.assertEqual(summary["total_records"], 0)
            self.assertEqual(summary["concentration_80_percent"], [])
            generate_population_report(Path(temporary) / "report", Path(temporary) / "empty.md")

    def test_missing_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "invalid.parquet"
            pd.DataFrame({"channel_id": ["c"]}).to_parquet(source, index=False)
            with self.assertRaisesRegex(ValueError, "missing columns"):
                characterize_population(source, Path(temporary) / "report")

    def test_no_usable_messages_and_unorderable_reply(self):
        row = {
            "guild_id": "g", "guild_name": "Guild", "channel_id": "c",
            "channel_name": "general", "message_id": "1", "author_id": "a",
            "is_bot": True, "message_type": 19, "content": "hello",
            "attachment_count": 0, "embed_count": 0, "sticker_count": 0,
            "referenced_message_id": "missing", "timestamp": "invalid",
        }
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "messages.parquet"
            output = Path(temporary) / "report"
            pd.DataFrame([row]).to_parquet(source, index=False)
            summary = characterize_population(source, output)
            self.assertEqual(summary["usable_human_messages"], 0)
            self.assertEqual(summary["unusable_records"], 0)
            self.assertIsNone(summary["native_reply_ratio_usable"])
            self.assertEqual(summary["native_replies_without_orderable_source"], 1)
            for item in summary["concentration_80_percent"]:
                if item["population"] == "usable_human":
                    self.assertIsNone(item["units_for_80_percent"])
            manifest = json.loads((output / "manifest.json").read_text())
            self.assertEqual(len(manifest["outputs"]), 6)
            generate_population_report(output, Path(temporary) / "no_usable.md")

    def test_only_absent_payload_is_unusable_regardless_of_type(self):
        base = {
            "guild_id": "g", "guild_name": "Guild", "channel_id": "c",
            "channel_name": "general", "author_id": "a", "is_bot": False,
            "timestamp": "2026-01-01T00:00:00Z", "content": "text",
            "attachment_count": 0, "embed_count": 0, "sticker_count": 0,
            "referenced_message_id": None,
        }
        rows = [
            {**base, "message_id": "1", "message_type": 21},
            {**base, "message_id": "2", "message_type": 6, "content": "  "},
            {**base, "message_id": "3", "message_type": None, "content": None, "attachment_count": 1},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "messages.parquet"
            pd.DataFrame(rows).to_parquet(source, index=False)
            summary = characterize_population(source, Path(temporary) / "report")
            self.assertEqual(summary["usable_human_messages"], 2)
            self.assertEqual(summary["unusable_records"], 1)
            self.assertEqual(summary["missing_payload_records"], 1)
            self.assertEqual(summary["other_or_unknown_type_records"], 3)

    def test_report_calculations_and_markdown_escaping(self):
        equal = concentration_statistics(pd.Series([10, 10]))
        self.assertEqual(equal["gini"], 0)
        self.assertEqual(equal["hhi"], 0.5)
        self.assertEqual(equal["effective_units"], 2)
        self.assertEqual(equal["thresholds"][1]["units"], 2)
        unequal = concentration_statistics(pd.Series([80, 20]))
        self.assertAlmostEqual(unequal["gini"], 0.3)
        self.assertAlmostEqual(unequal["hhi"], 0.68)
        self.assertEqual(unequal["thresholds"][1]["units"], 1)
        self.assertIsNone(concentration_statistics(pd.Series([0, 0]))["gini"])
        self.assertIn("a\\|b c", markdown_table(["Name"], [["a|b\nc"]]))