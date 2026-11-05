import tempfile
import unittest
from pathlib import Path

import pandas as pd

from discord_filtering.channel_selection import channel_decisions, select_channels, verify_selection


class ParticipantSelectionTests(unittest.TestCase):
    def test_strict_minima_use_or_and_manual_names_are_exact(self):
        statistics = pd.DataFrame([
            {"guild_id": "g", "guild_name": "Guild", "channel_id": str(index),
             "channel_name": name, "total_messages": messages, "distinct_human_authors": authors}
            for index, (name, messages, authors) in enumerate([
                ("small", 499, 5), ("few_authors", 500, 4), ("boundary", 500, 5),
                ("manual", 1000, 10), ("Manual", 1000, 10),
            ])
        ])
        result = channel_decisions(statistics, {"manual"})
        self.assertEqual(result.retained.tolist(), [False, False, True, False, True])
        self.assertEqual(result.decision_reason.tolist(), ["too_few_messages", "too_few_participants", "retained", "manual_name", "retained"])

    def test_invalid_counts_and_thresholds_are_rejected(self):
        base = {"guild_id": "g", "guild_name": "Guild", "channel_id": "c", "channel_name": "general", "total_messages": 500, "distinct_human_authors": 5}
        for value in (None, float("nan"), float("inf"), -1, 1.5, True, 501):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                channel_decisions(pd.DataFrame([{**base, "distinct_human_authors": value}]), set())
        with self.assertRaises(ValueError):
            channel_decisions(pd.DataFrame([base]), set(), minimum_human_authors=0)
        with self.assertRaises(ValueError):
            channel_decisions(pd.DataFrame([base, base]), set())

    def test_selection_recounts_participants_without_reply_or_mention_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "messages.parquet"
            exclusions = root / "exclusions.txt"
            exclusions.write_text("manual\n", encoding="utf-8")
            rows = []
            for channel, authors in (("good", ["a", "a", "b"]), ("few", ["a", "a", "a"]), ("manual", ["a", "b", "c"])):
                rows.extend({"guild_id": "g", "guild_name": "Guild", "channel_id": channel, "channel_name": channel,
                             "author_id": author, "is_bot": False} for author in authors)
            rows.extend([
                {"guild_id": "g", "guild_name": "Guild", "channel_id": "few", "channel_name": "few", "author_id": "bot", "is_bot": True},
                {"guild_id": "g", "guild_name": "Guild", "channel_id": "few", "channel_name": "few", "author_id": "unknown", "is_bot": None},
                {"guild_id": "g", "guild_name": "Guild", "channel_id": "few", "channel_name": "few", "author_id": " ", "is_bot": False},
            ])
            pd.DataFrame(rows).to_parquet(source, index=False)
            before = source.read_bytes()
            output = root / "selected"
            manifest = select_channels(source, exclusions, output, minimum_messages=3, minimum_human_authors=2)
            self.assertEqual(manifest["counts"]["retained_channels"], 1)
            self.assertEqual(manifest["counts"]["remaining_messages"], 3)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(verify_selection(output), manifest["counts"])
            statistics = pd.read_parquet(output / "channel_statistics.parquet")
            self.assertEqual(statistics.loc[statistics.channel_id == "few", "distinct_human_authors"].item(), 1)
            with self.assertRaises(FileExistsError):
                select_channels(source, exclusions, output)
            (output / "decisions.csv").write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_selection(output)