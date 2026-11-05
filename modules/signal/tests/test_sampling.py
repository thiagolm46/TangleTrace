import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from discord_disentanglement.annotation_bundle import build_annotation_bundle, publish_annotation_dataset
from discord_disentanglement.sampling import prepare_channel_frame, sample_corpus, select_hierarchical_windows
from discord_disentanglement.sampling_audit import audit_sample, check_selection, context_sensitivity, known_total_variance, native_reply_diagnostics, window_diagnostics


class SamplingTests(unittest.TestCase):
    def make_frame(self):
        return pd.DataFrame([
            {"guild_id": guild, "channel_id": f"{guild}-{index}",
             "size_stratum": "small", "eligibility_status": "provisional_eligible"}
            for guild in ["a", "b"] for index in range(4)
        ])

    def make_candidates(self, frame):
        return pd.DataFrame([
            {"guild_id": channel.guild_id, "channel_id": channel.channel_id,
             "period": period, "window_index": index}
            for channel in frame.itertuples(index=False)
            for period in ["2026-01", "2026-02", "2026-03", "2026-04"]
            for index in range(5)
        ])

    def test_probabilities_and_reproducibility(self):
        frame = self.make_frame()
        candidates = self.make_candidates(frame)
        options = {"seed": 7, "channels_per_stratum": 2,
                   "periods_per_channel": 2, "windows_per_period": 1}
        channels, periods, windows = select_hierarchical_windows(frame, candidates, **options)
        self.assertEqual(channels.groupby("guild_id")["selected"].sum().to_dict(), {"a": 2, "b": 2})
        self.assertEqual(len(periods), 16)
        self.assertEqual(len(windows), 8)
        self.assertTrue(windows["channel_probability"].eq(0.5).all())
        self.assertTrue(windows["period_probability"].eq(0.5).all())
        self.assertTrue(windows["window_probability"].eq(0.2).all())
        self.assertTrue(windows["inclusion_probability"].eq(0.05).all())
        self.assertTrue(windows["design_weight"].eq(20).all())
        self.assertFalse(windows.duplicated(["guild_id", "channel_id", "period", "window_index"]).any())
        repeated = select_hierarchical_windows(
            frame.sample(frac=1, random_state=4),
            candidates.sample(frac=1, random_state=4).reset_index(drop=True), **options,
        )
        for first, second in zip((channels, periods, windows), repeated):
            pd.testing.assert_frame_equal(first.reset_index(drop=True), second.reset_index(drop=True))

    def test_statuses_size_coverage_and_technical_exclusions(self):
        frame = self.make_frame()
        frame.loc[0, "eligibility_status"] = "pending_review"
        frame.loc[1, "eligibility_status"] = "excluded"
        frame.loc[2, "size_stratum"] = "large"
        frame.loc[3, "size_stratum"] = "medium"
        candidates = self.make_candidates(frame)
        candidates = candidates.loc[candidates.channel_id != "b-3"]
        channels, _, windows = select_hierarchical_windows(frame, candidates, channels_per_stratum=1)
        self.assertFalse(channels.loc[channels.channel_id.isin(["a-0", "a-1", "b-3"]), "selected"].any())
        self.assertEqual(set(windows.loc[windows.guild_id == "a", "size_stratum"]), {"large", "medium"})
        self.assertEqual(channels.loc[channels.channel_id == "b-3", "technical_status"].item(), "no_valid_targets")
        self.assertTrue(windows.loc[windows.guild_id == "a", "channel_probability"].eq(1).all())

    def test_frame_is_separate_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "channels.csv"
            output = Path(temporary) / "eligibility.csv"
            pd.DataFrame({"guild_id": ["123"] * 5, "channel_id": ["1", "2", "3", "4", "5"],
                          "usable_human_messages": [0, 1000, 1001, 10000, 10001]}).to_csv(source, index=False)
            before = source.read_bytes()
            frame = prepare_channel_frame(source, output)
            self.assertEqual(frame["size_stratum"].tolist(), ["small", "small", "medium", "medium", "large"])
            self.assertTrue(frame["eligibility_status"].eq("provisional_eligible").all())
            self.assertEqual(before, source.read_bytes())
            with self.assertRaises(FileExistsError):
                prepare_channel_frame(source, output)

    def test_empty_and_invalid_frames(self):
        frame = self.make_frame()
        candidates = self.make_candidates(frame)
        frame["eligibility_status"] = "excluded"
        channels, periods, windows = select_hierarchical_windows(frame, candidates)
        self.assertFalse(channels["selected"].any())
        self.assertTrue(periods.empty)
        self.assertTrue(windows.empty)
        with self.assertRaisesRegex(ValueError, "quotas"):
            select_hierarchical_windows(frame, candidates, windows_per_period=0)
        frame.loc[0, "eligibility_status"] = "typo"
        with self.assertRaisesRegex(ValueError, "eligibility_status"):
            select_hierarchical_windows(frame, candidates)

    def test_parquet_draw_short_windows_context_and_bundle(self):
        base = {
            "guild_id": "123456789012345678", "guild_name": "Guild", "channel_id": "987654321098765432",
            "channel_name": "general", "author_id": "a", "is_bot": False, "message_type": 0,
            "content": "hello", "attachment_count": 0, "embed_count": 0, "sticker_count": 0,
            "referenced_message_id": None,
        }
        rows = [
            {**base, "message_id": "1", "timestamp": "2026-01-31T23:58:00Z"},
            {**base, "message_id": "2", "timestamp": "2026-01-31T23:59:00Z", "is_bot": True},
            {**base, "message_id": "3", "timestamp": "2026-02-01T00:00:00Z",
             "message_type": 19, "referenced_message_id": "1"},
            {**base, "message_id": "4", "timestamp": "2026-02-01T00:00:30Z", "content": "", "is_bot": None},
            {**base, "message_id": "5", "timestamp": "2026-02-01T00:01:00Z", "content": "", "attachment_count": 1,
             "attachments_json": '[{"url": "https://example.org/image.png"}]'},
            {**base, "message_id": "6", "timestamp": "2026-02-01T00:02:00Z"},
            {**base, "message_id": "duplicate", "timestamp": "2026-02-01T00:03:00Z"},
            {**base, "message_id": "duplicate", "timestamp": "2026-02-01T00:04:00Z"},
            {**base, "message_id": "invalid", "timestamp": "bad"},
            {**base, "message_id": "missing_author", "timestamp": "2026-02-01T00:05:00Z", "author_id": None},
            {**base, "message_id": "unknown_bot", "timestamp": "2026-02-01T00:06:00Z", "is_bot": None},
            {**base, "message_id": "no_payload", "timestamp": "2026-02-01T00:07:00Z", "content": "  "},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "messages.parquet"
            frame_path = root / "frame.csv"
            pd.DataFrame(rows).to_parquet(source, index=False)
            pd.DataFrame([{**base, "size_stratum": "small", "eligibility_status": "provisional_eligible",
                           "usable_human_messages": 8, "small_max": 1000, "medium_max": 10000}]).to_csv(frame_path, index=False)
            original = source.read_bytes()
            options = {"target_messages": 2, "context_messages": 2, "windows_per_period": 10}
            manifest = sample_corpus(source, frame_path, root / "draw", **options)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(manifest["counts"]["target_messages"], 4)
            self.assertEqual(manifest["counts"]["selected_windows"], 3)
            windows = pd.read_csv(root / "draw/selected_windows.csv")
            self.assertEqual(sorted(windows["annotated_message_count"].tolist()), [1, 1, 2])
            self.assertTrue(windows["inclusion_probability"].eq(1).all())
            messages = pd.read_parquet(root / "draw/sampled_messages.parquet")
            self.assertEqual(set(messages.loc[~messages.is_context, "message_id"]), {"1", "3", "5", "6"})
            self.assertTrue(messages.loc[messages.is_context, "target_inclusion_probability"].isna().all())
            exported = pd.read_csv(root / "draw/annotation_windows.csv")
            february = exported.loc[exported.first_annotated_message_id == 3].iloc[0]
            payload = json.loads(february.messages_json)
            self.assertEqual([item["message_id"] for item in payload], ["1", "2", "3", "4", "5"])
            self.assertEqual(payload[2]["native_reply_to_message_id"], "1")
            self.assertEqual(payload[-1]["attachments"][0]["url"], "https://example.org/image.png")
            bundle = build_annotation_bundle(root / "draw/annotation_windows.csv", root / "bundle")
            self.assertEqual(len(pd.read_parquet(bundle.source_statuses_path)), 4)
            native_edges = root / "native_edges.parquet"
            pd.DataFrame([{"source_message_id": "3", "target_message_id": "1"}]).to_parquet(native_edges, index=False)
            codebook = root / "CODEBOOK.md"
            codebook.write_text("# Annotation protocol\n", encoding="utf-8")
            published = publish_annotation_dataset(root / "bundle", native_edges, codebook, root / "published")
            publication = json.loads(published.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(publication["counts"]["human_annotation_edge_count"], 0)
            self.assertEqual(publication["counts"]["silver_native_reply_edge_count"], 1)
            self.assertEqual(len(publication["files"]), 6)
            with self.assertRaises(FileExistsError):
                publish_annotation_dataset(root / "bundle", native_edges, codebook, root / "published")
            sample_corpus(source, frame_path, root / "repeated", **options)
            self.assertEqual((root / "draw/selected_windows.csv").read_bytes(), (root / "repeated/selected_windows.csv").read_bytes())
            sample_corpus(source, frame_path, root / "subsample", target_messages=2,
                          periods_per_channel=1, windows_per_period=1)
            subsample = pd.read_csv(root / "subsample/selected_windows.csv")
            self.assertEqual(len(subsample), 1)
            self.assertEqual(subsample["period_probability"].item(), 0.5)
            self.assertEqual(subsample["inclusion_probability"].item(), 0.5 / subsample["windows_in_period"].item())
            diagnosed = window_diagnostics(messages, windows)
            self.assertEqual(diagnosed.target_count.sum(), 4)
            self.assertEqual(diagnosed.visible_native_target_edges.sum(), 1)
            replies, technical = native_reply_diagnostics(messages, windows, source)
            self.assertEqual(replies.status.tolist(), ["visible"])
            self.assertEqual(technical.technical_targets.sum(), 4)
            coverage = context_sensitivity(replies, [0, 1, 2, 200])
            self.assertEqual(coverage.visible_references.tolist(), [0, 0, 1, 1])
            audit = audit_sample(root / "draw", root / "audit", root / "report.md")
            self.assertTrue(audit["all_checks_passed"])
            self.assertEqual(audit["target_messages"], 4)
            self.assertIn("Sampling design", (root / "report.md").read_text(encoding="utf-8"))
            with self.assertRaises(FileExistsError):
                audit_sample(root / "draw", root / "audit", root / "report.md")
            repeated_audit = audit_sample(root / "draw", root / "repeated_audit", root / "report.md", overwrite_report=True)
            self.assertTrue(repeated_audit["all_checks_passed"])
            self.assertTrue((root / "repeated_audit/manifest.json").is_file())
            (root / "draw/selected_windows.csv").write_text("tampered", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                audit_sample(root / "draw", root / "tampered_audit", root / "other.md")
            with self.assertRaises(FileExistsError):
                sample_corpus(source, frame_path, root / "draw", **options)

    def test_independent_design_audit_detects_wrong_probabilities(self):
        frame = self.make_frame()
        candidates = self.make_candidates(frame)
        candidates["annotated_message_count"] = 2
        candidates["first_position"] = candidates.window_index * 2 + 1
        candidates["last_position"] = candidates.first_position + 1
        options = {"channels_per_stratum": 2, "periods_per_channel": 2,
                   "windows_per_period": 1, "target_messages": 2}
        channels, periods, windows = select_hierarchical_windows(
            frame, candidates, **{key: value for key, value in options.items() if key != "target_messages"},
        )
        checks, expected = check_selection(frame, candidates, channels, periods, windows, options)
        self.assertTrue(checks.passed.all(), checks.loc[~checks.passed].to_dict("records"))
        self.assertAlmostEqual(expected.inclusion_probability.sum(), 8)
        self.assertAlmostEqual((expected.inclusion_probability * expected.design_weight * expected.annotated_message_count).sum(), 320)
        windows.loc[0, "design_weight"] *= 2
        checks, _ = check_selection(frame, candidates, channels, periods, windows, options)
        self.assertFalse(checks.loc[checks.check == "design_weight_per_window", "passed"].item())

    def test_native_interleaving_is_only_an_observable_proxy(self):
        rows = [
            {"message_id": "1", "author_id": "a", "is_context": True, "referenced_message_id": None},
            {"message_id": "2", "author_id": "b", "is_context": True, "referenced_message_id": None},
            {"message_id": "3", "author_id": "a", "is_context": False, "referenced_message_id": "1"},
            {"message_id": "4", "author_id": "b", "is_context": False, "referenced_message_id": "2"},
        ]
        messages = pd.DataFrame([
            {**row, "annotation_id": "sample", "guild_id": "g", "channel_id": "c",
             "message_type": 19 if row["referenced_message_id"] else 0, "position": index,
             "timestamp": f"2026-01-01T00:0{index}:00Z"}
            for index, row in enumerate(rows)
        ])
        messages.loc[0, "timestamp"] = "2026-01-01T00:00:00.123Z"
        windows = pd.DataFrame([{"annotation_id": "sample", "size_stratum": "small", "period": "2026-01",
                                 "inclusion_probability": 1.0, "design_weight": 1.0}])
        result = window_diagnostics(messages, windows).iloc[0]
        self.assertEqual(result.native_components_touching_targets, 2)
        self.assertEqual(result.overlapping_native_component_pairs, 1)
        self.assertEqual(result.crossing_native_target_edge_pairs, 1)
        self.assertEqual(result.target_duration_hours, 1 / 60)

    def test_exact_known_total_variance_and_census(self):
        expected = pd.DataFrame([
            {"guild_id": "g", "channel_id": "c", "period": "2026-01", "size_stratum": "small",
             "windows_drawn": 1, "periods_drawn": 1, "channels_drawn": 1, "annotated_message_count": count}
            for count in [1, 3]
        ])
        ht = known_total_variance(expected, "annotated_message_count", expanded=True)
        raw = known_total_variance(expected, "annotated_message_count", expanded=False)
        self.assertEqual(ht["mean"], 4)
        self.assertEqual(ht["variance"], 4)
        self.assertEqual(raw["mean"], 2)
        self.assertEqual(raw["variance"], 1)
        expected["windows_drawn"] = 2
        census = known_total_variance(expected, "annotated_message_count", expanded=True)
        self.assertEqual(census["mean"], 4)
        self.assertEqual(census["variance"], 0)

    def test_exact_variance_across_three_stages(self):
        expected = pd.DataFrame([
            {"guild_id": "g", "channel_id": channel, "period": period, "size_stratum": "small",
             "windows_drawn": 1, "periods_drawn": 1, "channels_drawn": 1,
             "annotated_message_count": count}
            for channel, period, counts in [("a", "2026-01", [1, 3]), ("a", "2026-02", [2, 6]),
                                            ("b", "2026-01", [4, 8]), ("b", "2026-02", [5, 7])]
            for count in counts
        ])
        moments = known_total_variance(expected, "annotated_message_count", expanded=True)
        outcomes = expected.annotated_message_count.to_numpy() * 8
        self.assertEqual(moments["mean"], outcomes.mean())
        self.assertEqual(moments["variance"], outcomes.var(ddof=0))
        self.assertEqual(moments["variance"], sum(moments[field] for field in ("channel_variance", "period_variance", "window_variance")))