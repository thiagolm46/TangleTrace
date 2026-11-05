from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from discord_filtering import classify_server, load_profile
from discord_filtering.service import score_channels, write_channel_scoring_run
from discord_data.extraction import load_selected_servers


ROOT = Path(__file__).resolve().parents[1]
SOFTWARE_PROFILE = ROOT / "configs" / "filtering" / "software.v1.json"


class ServerSelectionTests(unittest.TestCase):
    def test_profile_max_negative_score_excludes_noisy_candidate(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        record = {
            "id": "1",
            "name": "Open source programming github framework crypto giveaway",
            "description": "software development community",
            "keywords": [],
        }

        result = classify_server(record, profile)

        self.assertGreaterEqual(
            result.positive_score,
            profile.server.selection.min_positive_score,
        )
        self.assertGreater(
            result.negative_score,
            profile.server.selection.max_negative_score,
        )
        self.assertFalse(result.is_selected)

    def test_extraction_ignores_rejected_rows_from_audit_artifact(self) -> None:
        rows = [
            {
                "guild_id": "selected",
                "name": "Selected",
                "positive_score": 10,
                "matched_positive_terms": "[]",
                "is_selected": True,
            },
            {
                "guild_id": "rejected",
                "name": "Rejected",
                "positive_score": 12,
                "matched_positive_terms": "[]",
                "is_selected": False,
            },
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            artifact = Path(temp_dir) / "servers.parquet"
            pd.DataFrame(rows).to_parquet(artifact, index=False)

            lookup, selected_ids = load_selected_servers(artifact)

        self.assertEqual(selected_ids, {"selected"})
        self.assertEqual(set(lookup), {"selected"})


class ChannelScoringTests(unittest.TestCase):
    def test_all_channels_are_preserved_and_low_volume_is_not_eligible(self) -> None:
        rows: list[dict[str, object]] = []
        for index in range(60):
            rows.append(
                {
                    "guild_id": "1",
                    "guild_name": "OSS Project",
                    "message_id": str(index),
                    "channel_id": "10",
                    "channel_name": "general",
                    "author_id": str(index % 4),
                    "is_bot": False,
                    "content": (
                        "pip install package config.py traceback TypeError "
                        "github.com/org/repo issue branch release open source"
                    ),
                }
            )
        for index in range(5):
            rows.append(
                {
                    "guild_id": "1",
                    "guild_name": "OSS Project",
                    "message_id": str(100 + index),
                    "channel_id": "11",
                    "channel_name": "memes",
                    "author_id": str(index % 4),
                    "is_bot": False,
                    "content": "lol weekend random meme",
                }
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            messages_path = Path(temp_dir) / "messages.parquet"
            pd.DataFrame(rows).to_parquet(messages_path, index=False)

            run = score_channels(
                messages_path,
                SOFTWARE_PROFILE,
                min_messages=50,
                all_guilds=True,
            )
            output_path = Path(temp_dir) / "channels.parquet"
            _, manifest_path = write_channel_scoring_run(
                run,
                input_path=messages_path,
                profile_path=SOFTWARE_PROFILE,
                output_path=output_path,
                min_messages=50,
                guild_name=None,
                guild_id=None,
                all_guilds=True,
            )
            manifest_counts = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )["counts"]

        by_name = {record["channel_name"]: record for record in run.records}
        self.assertEqual(set(by_name), {"general", "memes"})
        self.assertEqual(by_name["general"]["channel_class"], "A")
        self.assertTrue(by_name["general"]["meets_min_messages"])
        self.assertEqual(by_name["general"]["eligibility_status"], "eligible")

        low_volume = by_name["memes"]
        self.assertFalse(low_volume["meets_min_messages"])
        self.assertEqual(low_volume["eligibility_status"], "insufficient_data")
        self.assertFalse(low_volume["include_in_main_analysis"])
        self.assertTrue(low_volume["manual_review_required"])
        self.assertEqual(run.eligible_channels, 1)
        self.assertEqual(run.insufficient_channels, 1)
        self.assertEqual(
            manifest_counts,
            {
                "eligible_channels": 1,
                "insufficient_channels": 1,
                "source_rows_after_guild_filter": 65,
                "total_channels": 2,
            },
        )


if __name__ == "__main__":
    unittest.main()
