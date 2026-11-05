"""Hierarchical pilot: fixed servers, size-stratified channels, months, windows.

Run from the project root with the project Python environment:
    python -m discord_disentanglement.sampling prepare-frame
    python -m discord_disentanglement.sampling draw --help
    python -m pytest tests/test_sampling.py -q

The default quotas are operational pilot settings, not a precision guarantee.
All frame review decisions and all sampling artifacts live outside the source
Parquet. Pending/excluded channels are retained in the register for auditing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

from discord_disentanglement.population import DEFAULT_INPUT, DEFAULT_OUTPUT, REQUIRED_COLUMNS
from discord_filtering.storage import atomic_write_bytes, sha256_file


ELIGIBILITY_STATUSES = {"provisional_eligible", "eligible", "pending_review", "excluded"}
INCLUDED_STATUSES = {"provisional_eligible", "eligible"}
CHANNEL_KEY = ["guild_id", "channel_id"]
PERIOD_KEY = [*CHANNEL_KEY, "period"]
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRAME = ROOT / "annotations/channel_frame_participants_v2.csv"
DEFAULT_SAMPLE = ROOT / "data/processed/disentanglement/sampling_participants_v2"


def prepare_channel_frame(
    channels_path: str | Path,
    output_path: str | Path,
    *,
    small_max: int = 1_000,
    medium_max: int = 10_000,
) -> pd.DataFrame:
    """Create a separate, editable eligibility register; never edit the corpus."""
    if not 0 < small_max < medium_max:
        raise ValueError("require 0 < small_max < medium_max")
    output = Path(output_path)
    if output.exists():
        raise FileExistsError(output)
    frame = pd.read_csv(channels_path, dtype={"guild_id": str, "channel_id": str})
    _require_columns(frame, {*CHANNEL_KEY, "usable_human_messages"})
    counts = pd.to_numeric(frame["usable_human_messages"], errors="raise")
    if counts.isna().any() or (counts < 0).any() or (counts % 1 != 0).any():
        raise ValueError("usable_human_messages must be nonnegative integers")
    frame["size_stratum"] = [
        "small" if count <= small_max else "medium" if count <= medium_max else "large"
        for count in counts
    ]
    frame["small_max"] = small_max
    frame["medium_max"] = medium_max
    frame["eligibility_status"] = "provisional_eligible"
    frame["eligibility_reason"] = "Awaiting scope review; participant-count selection"
    _validate_channel_frame(frame)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return frame


def select_hierarchical_windows(
    channel_frame: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    seed: int = 20261014,
    channels_per_stratum: int = 2,
    periods_per_channel: int = 3,
    windows_per_period: int = 1,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """SRS without replacement at each stage, conditional on the frozen frame."""
    quotas = (channels_per_stratum, periods_per_channel, windows_per_period)
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in quotas):
        raise ValueError("sampling quotas must be positive integers")
    _validate_channel_frame(channel_frame)
    _require_columns(candidates, {*PERIOD_KEY, "window_index"})
    candidates = candidates.sort_values([*PERIOD_KEY, "window_index"]).reset_index(drop=True)
    if candidates.duplicated([*PERIOD_KEY, "window_index"]).any():
        raise ValueError("duplicate candidate window")
    if candidates[[*PERIOD_KEY, "window_index"]].isna().any().any():
        raise ValueError("candidate identifiers cannot be missing")
    available = candidates.groupby(CHANNEL_KEY).size().rename("candidate_windows")
    channels = channel_frame.sort_values(CHANNEL_KEY).reset_index(drop=True).copy()
    channels = channels.merge(available, on=CHANNEL_KEY, how="left", validate="one_to_one")
    channels["candidate_windows"] = channels["candidate_windows"].fillna(0).astype(int)
    channels["technical_status"] = channels["candidate_windows"].map(
        lambda count: "ready" if count else "no_valid_targets"
    )
    channels["selected"] = False
    channels["channels_in_stratum"] = 0
    channels["channels_drawn"] = 0
    channels["channel_probability"] = 0.0
    eligible = channels[
        channels["eligibility_status"].isin(INCLUDED_STATUSES)
        & (channels["candidate_windows"] > 0)
    ]
    generator = random.Random(seed)
    for _, group in eligible.groupby(["guild_id", "size_stratum"], sort=True):
        population = len(group)
        drawn = min(channels_per_stratum, population)
        channels.loc[group.index, "channels_in_stratum"] = population
        channels.loc[group.index, "channels_drawn"] = drawn
        channels.loc[group.index, "channel_probability"] = drawn / population
        chosen = generator.sample(group.index.tolist(), drawn)
        channels.loc[chosen, "selected"] = True

    period_rows = []
    window_rows = []
    for channel in channels.loc[channels["selected"]].itertuples(index=False):
        pool = candidates[
            (candidates["guild_id"] == channel.guild_id)
            & (candidates["channel_id"] == channel.channel_id)
        ].sort_values(["period", "window_index"])
        periods = sorted(pool["period"].unique().tolist())
        periods_drawn = min(periods_per_channel, len(periods))
        chosen_periods = set(generator.sample(periods, periods_drawn))
        for period in periods:
            windows = pool.loc[pool["period"] == period]
            drawn = min(windows_per_period, len(windows))
            selected = period in chosen_periods
            record = {
                "guild_id": channel.guild_id,
                "channel_id": channel.channel_id,
                "size_stratum": channel.size_stratum,
                "period": period,
                "periods_in_channel": len(periods),
                "periods_drawn": periods_drawn,
                "period_probability": periods_drawn / len(periods),
                "channel_probability": channel.channel_probability,
                "windows_in_period": len(windows),
                "windows_drawn": drawn,
                "selected": selected,
            }
            period_rows.append(record)
            if not selected:
                continue
            chosen = sorted(generator.sample(windows.index.tolist(), drawn))
            for index in chosen:
                window = windows.loc[index].to_dict()
                probability = channel.channel_probability * record["period_probability"] * drawn / len(windows)
                window.update(record)
                window.update({
                    "window_probability": drawn / len(windows),
                    "inclusion_probability": probability,
                    "design_weight": 1.0 / probability,
                    "seed": seed,
                })
                window_rows.append(window)
    period_columns = [
        *PERIOD_KEY, "size_stratum", "periods_in_channel", "periods_drawn",
        "period_probability", "channel_probability", "windows_in_period",
        "windows_drawn", "selected",
    ]
    window_columns = list(dict.fromkeys([
        *candidates.columns, *period_columns, "window_probability",
        "inclusion_probability", "design_weight", "seed",
    ]))
    return (
        channels,
        pd.DataFrame(period_rows, columns=period_columns),
        pd.DataFrame(window_rows, columns=window_columns),
    )


def sample_corpus(
    input_path: str | Path,
    frame_path: str | Path,
    output_dir: str | Path,
    *,
    seed: int = 20261014,
    channels_per_stratum: int = 2,
    periods_per_channel: int = 3,
    windows_per_period: int = 1,
    target_messages: int = 100,
    context_messages: int = 200,
    memory_limit: str = "2GB",
) -> dict:
    """Draw an auditable pilot from a read-only Parquet using disk-backed DuckDB."""
    if target_messages < 1 or context_messages < 0:
        raise ValueError("require target_messages > 0 and context_messages >= 0")
    source = Path(input_path).resolve()
    register = Path(frame_path).resolve()
    output = Path(output_dir).resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    frame = pd.read_csv(register, dtype={"guild_id": str, "channel_id": str}, keep_default_na=False)
    _validate_channel_frame(frame)
    if output.exists():
        raise FileExistsError(f"use a new output directory: {output}")
    input_hash = sha256_file(source)
    frame_bytes = register.read_bytes()
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix=".sampling-", dir=output) as temporary:
        with duckdb.connect(str(Path(temporary) / "sampling.duckdb")) as connection:
            connection.execute("SET memory_limit = ?", [memory_limit])
            connection.execute("SET TimeZone = 'UTC'")
            connection.execute("SET temp_directory = ?", [temporary])
            connection.execute("SET threads = 2")
            connection.execute("SET preserve_insertion_order = false")
            connection.from_parquet(str(source)).create_view("source")
            columns = {row[0] for row in connection.execute("DESCRIBE source").fetchall()}
            missing = REQUIRED_COLUMNS - columns
            if missing:
                raise ValueError(f"missing columns: {', '.join(sorted(missing))}")
            connection.execute("""
                CREATE TABLE ordered AS
                WITH normalized AS (
                    SELECT nullif(trim(cast(guild_id AS VARCHAR)), '') AS guild_id,
                           nullif(trim(cast(channel_id AS VARCHAR)), '') AS channel_id,
                           nullif(trim(cast(message_id AS VARCHAR)), '') AS message_id,
                           nullif(trim(cast(author_id AS VARCHAR)), '') AS author_id,
                           try_cast(timestamp AS TIMESTAMPTZ) AS sent_at,
                           coalesce(is_bot = false AND (
                               nullif(trim(content), '') IS NOT NULL
                               OR coalesce(attachment_count, 0) + coalesce(embed_count, 0)
                                   + coalesce(sticker_count, 0) > 0
                           ), false) AS usable
                    FROM source
                ), marked AS (
                    SELECT *, count(*) OVER (PARTITION BY guild_id, message_id) AS copies
                    FROM normalized
                )
                SELECT *, row_number() OVER (
                    PARTITION BY guild_id, channel_id ORDER BY sent_at, message_id
                ) AS position
                FROM marked WHERE guild_id IS NOT NULL AND channel_id IS NOT NULL
                    AND message_id IS NOT NULL AND author_id IS NOT NULL
                    AND sent_at IS NOT NULL AND copies = 1
            """)
            connection.execute("""
                CREATE TABLE targets AS
                SELECT *, strftime(sent_at, '%Y-%m') AS period,
                       (row_number() OVER (
                           PARTITION BY guild_id, channel_id, date_trunc('month', sent_at)
                           ORDER BY sent_at, message_id
                       ) - 1) // ? AS window_index
                FROM ordered WHERE usable
            """, [target_messages])
            candidates = connection.execute("""
                SELECT guild_id, channel_id, period, window_index,
                       min(position) AS first_position, max(position) AS last_position,
                       arg_min(message_id, position) AS first_annotated_message_id,
                       arg_max(message_id, position) AS last_annotated_message_id,
                       min(sent_at) AS annotation_start_timestamp,
                       max(sent_at) AS annotation_end_timestamp,
                       count(*) AS annotated_message_count
                FROM targets GROUP BY guild_id, channel_id, period, window_index
                ORDER BY guild_id, channel_id, period, window_index
            """).fetchdf()
            channels, periods, windows = select_hierarchical_windows(
                frame, candidates, seed=seed, channels_per_stratum=channels_per_stratum,
                periods_per_channel=periods_per_channel, windows_per_period=windows_per_period,
            )
            if windows.empty:
                raise ValueError("no sampleable channels: check eligibility and technical_status")
            windows["annotation_id"] = [
                "SAMPLE_" + hashlib.sha256(json.dumps([
                    row.guild_id, row.channel_id, row.first_annotated_message_id,
                    row.last_annotated_message_id,
                ]).encode("utf-8")).hexdigest()[:20]
                for row in windows.itertuples(index=False)
            ]
            connection.register("selected_windows", windows)
            connection.execute("""
                CREATE TABLE memberships AS
                SELECT selected.annotation_id, messages.guild_id, messages.channel_id,
                       messages.message_id, messages.position,
                       NOT (messages.usable AND messages.position >= selected.first_position)
                           AS is_context,
                       CASE WHEN messages.usable AND messages.position >= selected.first_position
                            THEN selected.inclusion_probability END AS target_inclusion_probability,
                       CASE WHEN messages.usable AND messages.position >= selected.first_position
                            THEN selected.design_weight END AS target_design_weight
                FROM selected_windows selected JOIN ordered messages
                    ON messages.guild_id = selected.guild_id
                    AND messages.channel_id = selected.channel_id
                    AND messages.position BETWEEN greatest(1, selected.first_position - ?)
                        AND selected.last_position
            """, [context_messages])
            messages = connection.execute("""
                SELECT source.*, members.annotation_id, members.position, members.is_context,
                       members.target_inclusion_probability, members.target_design_weight
                FROM source JOIN memberships members
                    ON trim(cast(source.guild_id AS VARCHAR)) = members.guild_id
                    AND trim(cast(source.channel_id AS VARCHAR)) = members.channel_id
                    AND trim(cast(source.message_id AS VARCHAR)) = members.message_id
                ORDER BY members.annotation_id, members.position
            """).fetchdf()
    candidates.to_csv(output / "window_frame.csv", index=False)
    channels.to_csv(output / "channel_selection.csv", index=False)
    periods.to_csv(output / "period_selection.csv", index=False)
    windows.to_csv(output / "selected_windows.csv", index=False)
    messages.to_parquet(output / "sampled_messages.parquet", index=False)
    _annotation_windows(windows, messages).to_csv(output / "annotation_windows.csv", index=False)
    atomic_write_bytes(output / "channel_frame.csv", frame_bytes)
    filenames = [
        "window_frame.csv", "channel_selection.csv", "period_selection.csv",
        "selected_windows.csv", "sampled_messages.parquet", "annotation_windows.csv", "channel_frame.csv",
    ]
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_path": str(source), "input_sha256": input_hash,
        "frame_path": str(register), "frame_sha256": hashlib.sha256(frame_bytes).hexdigest(),
        "implementation_sha256": sha256_file(Path(__file__)),
        "python_version": sys.version, "duckdb_version": duckdb.__version__, "pandas_version": pd.__version__,
        "parameters": {
            "seed": seed, "channels_per_stratum": channels_per_stratum,
            "periods_per_channel": periods_per_channel, "windows_per_period": windows_per_period,
            "target_messages": target_messages, "context_messages": context_messages, "memory_limit": memory_limit,
        },
        "design": {
            "scope": "provisional pilot; conditional on retained servers, not a sample of all Discord",
            "servers": "fixed, inclusion probability 1 within this frame",
            "channel_strata": "guild_id x size_stratum; equal channel quota, no volume PPS",
            "periods": "observed UTC calendar months with at least one valid target",
            "windows": "nonoverlapping blocks of human usable targets per month, including the short final block",
            "selection": "simple random sampling without replacement at each of three stages",
            "included_statuses": sorted(INCLUDED_STATUSES),
            "technical_requirements": "nonempty guild/channel/message/author IDs, valid UTC timestamp, unique (guild_id, message_id)",
            "target_population": "payload_v2 usable humans satisfying technical requirements, in included channels",
            "probability": "(channels_drawn/channels_in_stratum) * (periods_drawn/periods_in_channel) * (windows_drawn/windows_in_period)",
            "design_weight": "1 / inclusion_probability; same for each target in its unique block",
            "context": "up to context_messages preceding valid records plus in-span nontargets; no target probability assigned to context membership",
            "inference": "weights support message totals/ratios within this frame; channel means need a declared estimator; clustered uncertainty required",
            "substitutions": "none; eligibility changes require a new frozen frame and a new run",
        },
        "counts": {
            "frame_channels": len(frame), "selected_channels": int(channels["selected"].sum()),
            "selected_servers": int(channels.loc[channels["selected"], "guild_id"].nunique()),
            "selected_windows": len(windows), "target_messages": int(windows["annotated_message_count"].sum()),
            "context_memberships": int(messages["is_context"].sum()),
            "channels_without_valid_targets": int(channels["candidate_windows"].eq(0).sum()),
        },
        "outputs": {filename: sha256_file(output / filename) for filename in filenames},
    }
    atomic_write_bytes(output / "manifest.json", (json.dumps(manifest, indent=2, ensure_ascii=True) + "\n").encode("utf-8"))
    return manifest


def _annotation_windows(windows: pd.DataFrame, messages: pd.DataFrame) -> pd.DataFrame:
    rows = []
    membership_columns = {"annotation_id", "position", "is_context", "target_inclusion_probability", "target_design_weight"}
    for annotation_id, group in messages.groupby("annotation_id", sort=True):
        metadata = windows.loc[windows["annotation_id"] == annotation_id].iloc[0].to_dict()
        payload = []
        cleaned = group.astype(object).where(pd.notna(group), None)
        for sequence, message in enumerate(cleaned.to_dict(orient="records"), start=1):
            raw = {key: value for key, value in message.items() if key not in membership_columns}
            target = raw.get("referenced_message_id") if raw.get("message_type") == 19 else None
            target = str(target).strip() if target is not None else None
            item = {
                **raw, "sequence": sequence,
                "window_role": "context" if message["is_context"] else "annotated",
                "requires_reply_annotation": not message["is_context"],
                "server_id": str(raw["guild_id"]).strip(),
                "guild_id": str(raw["guild_id"]).strip(),
                "channel_id": str(raw["channel_id"]).strip(),
                "message_id": str(raw["message_id"]).strip(),
                "author_id": str(raw["author_id"]).strip(),
                "timestamp": pd.to_datetime(raw["timestamp"], utc=True).isoformat(),
                "native_reply_to_message_id": target or None,
                "native_reply_evidence": "positive_observed" if target else "unknown",
                "native_available_fields": sorted(raw),
                "native_fields_json": json.dumps(raw, ensure_ascii=True, default=str),
                "target_inclusion_probability": message["target_inclusion_probability"],
                "target_design_weight": message["target_design_weight"],
            }
            for field in ("attachments", "embeds", "mentions", "mention_roles", "sticker_items", "reactions"):
                item[field] = json.loads(raw.get(f"{field}_json") or "[]")
            payload.append(item)
        metadata.update({
            "window_id": annotation_id,
            "guild_name": payload[0].get("guild_name"), "channel_name": payload[0].get("channel_name"),
            "context_message_count": int(group["is_context"].sum()), "total_message_count": len(group),
            "messages_json": json.dumps(payload, ensure_ascii=True, default=str),
            "human_reply_edges_json": "[]", "human_reply_source_statuses_json": "[]",
            "annotator_id": "", "reviewed_at": "", "notes": "",
        })
        rows.append(metadata)
    return pd.DataFrame(rows)


def _require_columns(frame: pd.DataFrame, columns: set[str]) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise ValueError(f"missing columns: {', '.join(sorted(missing))}")


def _validate_channel_frame(frame: pd.DataFrame) -> None:
    _require_columns(frame, {*CHANNEL_KEY, "size_stratum", "eligibility_status"})
    if frame[CHANNEL_KEY].isna().any().any() or frame[CHANNEL_KEY].eq("").any().any():
        raise ValueError("channel identifiers cannot be missing")
    if frame.duplicated(CHANNEL_KEY).any():
        raise ValueError("duplicate channel in frame")
    if not frame["eligibility_status"].isin(ELIGIBILITY_STATUSES).all():
        raise ValueError("invalid eligibility_status")
    if not frame["size_stratum"].isin({"small", "medium", "large"}).all():
        raise ValueError("invalid size_stratum")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Reproducible hierarchical stratified sampling; input Parquet is never modified.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-frame", help="Create the provisional channel eligibility CSV for review.")
    prepare.add_argument("--channels", type=Path, default=DEFAULT_OUTPUT / "channels.csv")
    prepare.add_argument("--output", type=Path, default=DEFAULT_FRAME)
    prepare.add_argument("--small-max", type=int, default=1_000)
    prepare.add_argument("--medium-max", type=int, default=10_000)
    draw = commands.add_parser("draw", help="Draw a pilot, freeze the frame and export windows, messages and probabilities.")
    draw.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    draw.add_argument("--frame", type=Path, default=DEFAULT_FRAME)
    draw.add_argument("--output", type=Path, default=DEFAULT_SAMPLE)
    draw.add_argument("--seed", type=int, default=20261014)
    draw.add_argument("--channels-per-stratum", type=int, default=2)
    draw.add_argument("--periods-per-channel", type=int, default=3)
    draw.add_argument("--windows-per-period", type=int, default=1)
    draw.add_argument("--target-messages", type=int, default=100)
    draw.add_argument("--context-messages", type=int, default=200)
    draw.add_argument("--memory-limit", default="2GB")
    arguments = parser.parse_args(argv)
    if arguments.command == "prepare-frame":
        frame = prepare_channel_frame(arguments.channels, arguments.output, small_max=arguments.small_max, medium_max=arguments.medium_max)
        print(json.dumps({"frame_channels": len(frame), "output": str(arguments.output)}, indent=2))
    else:
        manifest = sample_corpus(
            arguments.input, arguments.frame, arguments.output, seed=arguments.seed,
            channels_per_stratum=arguments.channels_per_stratum, periods_per_channel=arguments.periods_per_channel,
            windows_per_period=arguments.windows_per_period, target_messages=arguments.target_messages,
            context_messages=arguments.context_messages, memory_limit=arguments.memory_limit,
        )
        print(json.dumps({"output": str(arguments.output), **manifest["counts"]}, indent=2))


if __name__ == "__main__":
    main()