from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from discord_filtering import (
    ProfileValidationError,
    classify_server,
    load_profile,
    profile_from_dict,
    score_channel,
)
from discord_filtering.storage import (
    OutputExistsError,
    build_manifest,
    sha256_file,
    write_records_with_manifest,
)
from discord_filtering.service import filter_servers


ROOT = Path(__file__).resolve().parents[1]
SOFTWARE_PROFILE = ROOT / "configs" / "filtering" / "software.v1.json"
SOFTWARE_ENGINEERING_PROFILE = ROOT / "configs" / "filtering" / "software.engineering.v1.json"
SOFTWARE_ENGINEERING_SCORING_PROFILE = ROOT / "configs" / "filtering" / "software.engineering.v2.json"


class ProfileValidationTests(unittest.TestCase):
    def test_software_profiles_use_the_validated_model(self) -> None:
        for path in (SOFTWARE_PROFILE, SOFTWARE_ENGINEERING_PROFILE, SOFTWARE_ENGINEERING_SCORING_PROFILE):
            with self.subTest(profile=path.name):
                profile = load_profile(path)
                self.assertEqual(profile.server.overlap_policy, "max_per_group")
                if path == SOFTWARE_ENGINEERING_SCORING_PROFILE:
                    self.assertIsNone(profile.channel)
                else:
                    self.assertEqual(profile.channel.overlap_policy, "max_per_group")

    def test_unknown_profile_keys_are_rejected(self) -> None:
        raw = json.loads(SOFTWARE_PROFILE.read_text(encoding="utf-8"))
        raw["unreviewed_option"] = True

        with self.assertRaises(ProfileValidationError):
            profile_from_dict(raw)


class ServerFilteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profile = load_profile(SOFTWARE_PROFILE)

    def test_keywords_accept_list_string_and_na(self) -> None:
        base = {"id": "1", "name": "Open Source", "description": None}
        from_list = classify_server({**base, "keywords": ["programming"]}, self.profile)
        from_string = classify_server({**base, "keywords": "programming"}, self.profile)
        from_na = classify_server({**base, "keywords": math.nan}, self.profile)
        from_sentinels = classify_server(
            {**base, "keywords": ["NA", "n/a", "null", "programming"]},
            self.profile,
        )

        self.assertTrue(from_list.is_selected)
        self.assertTrue(from_string.is_selected)
        self.assertEqual(from_list.positive_score, from_string.positive_score)
        self.assertEqual(from_na.keywords, ())
        self.assertEqual(from_sentinels.keywords, ("programming",))

    def test_cpp_csharp_boundaries_and_field_provenance(self) -> None:
        result = classify_server(
            {
                "id": "42",
                "name": "Software Development",
                "description": "Community for C++ and C# developers",
                "about": "DevOps collaboration",
                "reasons_to_join": ["Learn Ｐｙｔｈｏｎ", "Contribute code"],
                "keywords": ["open source"],
            },
            self.profile,
        )
        labels = {item.label for item in result.positive_evidence}
        evidence_fields = {item.field for item in result.positive_evidence}

        self.assertTrue(result.is_selected)
        self.assertTrue({"c++", "c#"}.issubset(labels))
        self.assertTrue(
            {"name", "description", "about", "reasons_to_join", "keywords"}.issubset(
                evidence_fields
            )
        )
        self.assertEqual(result.to_record()["about"], "DevOps collaboration")
        self.assertEqual(
            json.loads(result.to_record()["reasons_to_join_json"]),
            ["Learn Python", "Contribute code"],
        )

        false_boundary = classify_server(
            {"id": "43", "name": "abc++ and c##", "keywords": None},
            self.profile,
        )
        false_labels = {item.label for item in false_boundary.positive_evidence}
        self.assertNotIn("c++", false_labels)
        self.assertNotIn("c#", false_labels)

    def test_overlap_policy_credits_only_max_once_per_group(self) -> None:
        result = classify_server(
            {"id": "7", "name": "Programming and coding", "keywords": []},
            self.profile,
        )
        group_evidence = [
            item for item in result.positive_evidence if item.group == "programming-core"
        ]

        self.assertEqual(result.positive_score, 4.0)
        self.assertEqual(sum(item.credited_weight for item in group_evidence), 4.0)
        self.assertEqual({item.label for item in group_evidence}, {"programming", "coding"})

    def test_software_profile_accepts_generic_software_evidence(self) -> None:
        generic_software = classify_server(
            {"id": "8", "name": "Programming developers", "keywords": []},
            self.profile,
        )
        oss_server = classify_server(
            {"id": "9", "name": "Open source programming", "keywords": []},
            self.profile,
        )

        self.assertGreaterEqual(generic_software.positive_score, 7.0)
        self.assertTrue(generic_software.is_selected)
        self.assertTrue(oss_server.is_selected)

    def test_engineering_profile_prioritizes_curated_metadata_fields(self) -> None:
        profile = load_profile(SOFTWARE_ENGINEERING_PROFILE)
        result = classify_server(
            {
                "id": "10",
                "name": "Community",
                "description": "A place to meet people.",
                "reasons_to_join": ["Learn Python with peers"],
                "keywords": ["open source", "software engineering"],
            },
            profile,
        )
        irrelevant = classify_server(
            {"id": "11", "name": "Gaming community", "keywords": ["minecraft"]},
            profile,
        )

        self.assertTrue(result.is_selected)
        self.assertGreater(
            sum(item.credited_weight for item in result.positive_evidence if item.field == "keywords"),
            sum(item.credited_weight for item in result.positive_evidence if item.field == "reasons_to_join"),
        )
        self.assertFalse(irrelevant.is_selected)

    def test_scoring_profile_uses_confirmation_without_selection(self) -> None:
        profile = load_profile(SOFTWARE_ENGINEERING_SCORING_PROFILE)
        result = classify_server(
            {
                "id": "12",
                "name": "Python",
                "description": "Python Java Rust",
            },
            profile,
        )

        record = result.to_record()
        self.assertIsNone(profile.server.selection)
        self.assertIsNone(profile.channel)
        self.assertIsNone(result.is_selected)
        self.assertEqual(result.positive_groups, ("programming-language",))
        self.assertEqual(result.positive_score, 2.0)
        self.assertEqual(result.metadata_completeness, 0.4)
        self.assertEqual(
            json.loads(record["metadata_available_json"]),
            {
                "about": False,
                "description": True,
                "keywords": False,
                "name": True,
                "reasons_to_join": False,
            },
        )
        self.assertEqual(record["positive_group_count"], 1)
        self.assertEqual(record["software_positive_score"], result.positive_score)
        self.assertEqual(record["software_negative_score"], result.negative_score)
        self.assertEqual(record["software_affinity_score"], result.score_margin)

    def test_scoring_profile_emits_all_servers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "servers.json"
            input_path.write_text(
                json.dumps(
                    [
                        {"id": "positive", "name": "Software development"},
                        {"id": "negative", "name": "Minecraft trading"},
                    ]
                ),
                encoding="utf-8",
            )
            run = filter_servers(input_path, SOFTWARE_ENGINEERING_SCORING_PROFILE)

        self.assertEqual(run.evaluated_servers, 2)
        self.assertEqual(len(run.records), 2)
        self.assertEqual(run.selected_servers, 0)
        self.assertTrue(all(record["is_selected"] is None for record in run.records))
        self.assertLess(
            next(record for record in run.records if record["guild_id"] == "negative")[
                "software_affinity_score"
            ],
            0,
        )

    def test_scoring_profile_exports_separate_score_components(self) -> None:
        profile = load_profile(SOFTWARE_ENGINEERING_SCORING_PROFILE)
        result = classify_server(
            {
                "id": "hybrid",
                "name": "Software development for Minecraft",
            },
            profile,
        )

        record = result.to_record()
        self.assertGreater(record["software_positive_score"], 0.0)
        self.assertGreater(record["software_negative_score"], 0.0)
        self.assertEqual(
            record["software_affinity_score"],
            record["software_positive_score"] - record["software_negative_score"],
        )

    def test_scoring_profile_preserves_moderate_artifact_and_developer_evidence(self) -> None:
        profile = load_profile(SOFTWARE_ENGINEERING_SCORING_PROFILE)
        game_server = classify_server(
            {
                "id": "game",
                "name": "Official Fortnite Festival",
                "description": "Talk with fellow rhythm gamers and devs.",
            },
            profile,
        )
        artifact_server = classify_server(
            {
                "id": "artifact",
                "description": "A place for developers building plugins for a Python library.",
            },
            profile,
        )
        software_server = classify_server(
            {
                "id": "software",
                "description": (
                    "Comunidad de desarrolladores de software de codigo abierto "
                    "using automated testing, CI-CD, and GitHub."
                ),
            },
            profile,
        )
        game_development_server = classify_server(
            {"id": "game-dev", "description": "Independent game development community."},
            profile,
        )
        giveaway_server = classify_server(
            {"id": "giveaway", "description": "Daily giveaways for members."},
            profile,
        )
        trading_card_server = classify_server(
            {"id": "card", "description": "A trading card game community."},
            profile,
        )
        finance_server = classify_server(
            {"id": "finance", "description": "Forex trading signals and crypto news."},
            profile,
        )
        developer_community_server = classify_server(
            {"id": "developer-community", "description": "A developer community for developers."},
            profile,
        )

        self.assertIn("developer-community", game_server.positive_groups)
        self.assertLess(game_server.score_margin, 0.0)
        self.assertTrue(
            {"developer-community", "software-artifact", "programming-language"}.issubset(
                artifact_server.positive_groups
            )
        )
        self.assertIn("software-specialization", game_development_server.positive_groups)
        self.assertEqual(giveaway_server.negative_groups, ("promotion",))
        self.assertEqual(trading_card_server.negative_score, 0.0)
        self.assertEqual(finance_server.negative_groups, ("finance",))
        developer_credits = [
            evidence.credited_weight
            for evidence in developer_community_server.positive_evidence
            if evidence.group == "developer-community"
        ]
        self.assertEqual(sum(developer_credits), 6.25)
        self.assertTrue(
            {
                "software-intent",
                "developer-community",
                "open-source",
                "engineering-practice",
                "software-artifact",
            }.issubset(software_server.positive_groups)
        )


class ChannelScoringTests(unittest.TestCase):
    @staticmethod
    def _technical_messages(
        *,
        count: int,
        interactive: bool,
        bot: bool = False,
    ) -> list[dict[str, object]]:
        return [
            {
                "message_id": str(index),
                "author_id": str(index % 5),
                "is_bot": bot,
                "timestamp": f"{index:06d}",
                "referenced_message_id": str(index - 1) if interactive and index else None,
                "mention_count": 0,
                "content": (
                    "pip install package config.py traceback TypeError github.com/org/repo "
                    "issue branch release open source"
                ),
            }
            for index in range(count)
        ]

    def test_technical_channel_requires_conversation_evidence_for_inclusion(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        broadcast = score_channel(
            {"guild_id": "1", "channel_id": "10", "channel_name": "release-notes"},
            profile,
            messages=self._technical_messages(count=60, interactive=False),
        )
        conversation = score_channel(
            {"guild_id": "1", "channel_id": "11", "channel_name": "development"},
            profile,
            messages=self._technical_messages(count=60, interactive=True),
        )

        self.assertEqual(broadcast.channel_class, "A")
        self.assertFalse(broadcast.conversation_suitable)
        self.assertIn("low_interaction", broadcast.conversation_exclusion_reasons)
        self.assertFalse(broadcast.include_in_main_analysis)
        self.assertTrue(broadcast.manual_review_required)
        self.assertEqual(conversation.channel_class, "A")
        self.assertTrue(conversation.conversation_suitable)
        self.assertGreater(conversation.valid_native_reply_message_count, 0)
        self.assertGreater(conversation.author_transition_ratio, 0.2)
        self.assertTrue(conversation.include_in_main_analysis)

    def test_bot_dominated_channel_is_not_conversation_suitable(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        messages = self._technical_messages(count=60, interactive=True)
        messages.extend(self._technical_messages(count=100, interactive=True, bot=True))

        result = score_channel(
            {"guild_id": "1", "channel_id": "12", "channel_name": "development"},
            profile,
            messages=messages,
        )

        self.assertEqual(result.channel_class, "A")
        self.assertEqual(result.n_bot_messages, 100)
        self.assertGreater(result.bot_message_ratio, 0.5)
        self.assertFalse(result.conversation_suitable)
        self.assertIn("bot_dominated", result.conversation_exclusion_reasons)
        self.assertFalse(result.include_in_main_analysis)

    def test_single_author_dominance_is_not_conversation_suitable(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        messages = self._technical_messages(count=60, interactive=True)
        for index, message in enumerate(messages):
            message["author_id"] = "0" if index < 48 else str(index - 47)

        result = score_channel(
            {"guild_id": "1", "channel_id": "13", "channel_name": "development"},
            profile,
            messages=messages,
        )

        self.assertEqual(result.channel_class, "A")
        self.assertGreater(result.dominant_author_ratio, 0.7)
        self.assertIn("dominant_human_author", result.conversation_exclusion_reasons)
        self.assertFalse(result.conversation_suitable)

    def test_profiles_score_channels_with_one_pure_engine(self) -> None:
        software = load_profile(SOFTWARE_PROFILE)
        software_messages = [
            {
                "message_id": str(index),
                "author_id": str(index % 4),
                "is_bot": index == 0,
                "content": (
                    "pip install package config.py traceback TypeError github.com/org/repo "
                    "issue branch release open source"
                ),
            }
            for index in range(60)
        ]
        software_result = score_channel(
            {"guild_id": "1", "channel_id": "10", "channel_name": "general"},
            software,
            messages=software_messages,
        )

        self.assertEqual(software_result.channel_class, "A")
        self.assertEqual(software_result.n_messages, 59)
        self.assertEqual(software_result.n_bot_messages, 1)
        self.assertEqual(
            software_result.to_record()["software_channel_score"],
            software_result.channel_score,
        )
        self.assertLessEqual(
            max(len(signal.evidence) for signal in software_result.signal_scores),
            software.channel.max_evidence_examples,
        )



class ArtifactSafetyTests(unittest.TestCase):
    def test_atomic_output_has_hash_manifest_and_refuses_overwrite(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "source.json"
            source.write_text("[]\n", encoding="utf-8")
            output = directory / "result.json"
            manifest = build_manifest(
                command="test",
                profile_path=SOFTWARE_PROFILE,
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                domain=profile.domain,
                input_paths=[source],
                parameters={},
                counts={"rows": 1},
            )
            _, manifest_path = write_records_with_manifest(
                [{"guild_id": "1", "is_selected": True}],
                output,
                manifest,
            )
            saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(saved_manifest["output"]["sha256"], sha256_file(output))
            self.assertEqual(saved_manifest["source_data_policy"], "read_only_immutable")
            with self.assertRaises(OutputExistsError):
                write_records_with_manifest([], output, manifest)

    def test_atomic_parquet_output_is_fsynced_on_windows(self) -> None:
        profile = load_profile(SOFTWARE_PROFILE)
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "source.json"
            source.write_text("[]\n", encoding="utf-8")
            output = directory / "result.parquet"
            manifest = build_manifest(
                command="test-parquet",
                profile_path=SOFTWARE_PROFILE,
                profile_id=profile.profile_id,
                profile_version=profile.profile_version,
                domain=profile.domain,
                input_paths=[source],
                parameters={},
                counts={"rows": 1},
            )

            _, manifest_path = write_records_with_manifest(
                [{"guild_id": "1", "is_selected": True}],
                output,
                manifest,
            )

            self.assertTrue(output.exists())
            self.assertEqual(
                json.loads(manifest_path.read_text(encoding="utf-8"))["output"]["sha256"],
                sha256_file(output),
            )


if __name__ == "__main__":
    unittest.main()
