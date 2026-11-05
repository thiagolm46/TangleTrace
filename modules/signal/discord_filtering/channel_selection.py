from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from discord_filtering.storage import atomic_write_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data/processed/filtering/software/affinity_v2"
DEFAULT_SOURCE = SOURCE_DIR / "messages_2026-09-21.parquet"
DEFAULT_EXCLUSIONS = ROOT / "configs/filtering/channel_exclusions.v1.txt"
DEFAULT_OUTPUT = ROOT / "data/processed/filtering/software/participants_v2"
RULE_VERSION = "participants_min500_min5.v2"
REQUIRED_COLUMNS = {"guild_id", "guild_name", "channel_id", "channel_name", "author_id", "is_bot"}


def channel_decisions(
    statistics: pd.DataFrame,
    excluded_names: set[str],
    *,
    minimum_messages: int = 500,
    minimum_human_authors: int = 5,
) -> pd.DataFrame:
    for threshold in (minimum_messages, minimum_human_authors):
        if isinstance(threshold, bool) or not isinstance(threshold, int) or threshold < 1:
            raise ValueError("thresholds must be positive integers")
    required = {"guild_id", "guild_name", "channel_id", "channel_name", "total_messages", "distinct_human_authors"}
    if missing := required - set(statistics.columns):
        raise ValueError(f"missing statistics columns: {', '.join(sorted(missing))}")
    decisions = statistics.copy()
    for field in ("guild_id", "channel_id"):
        values = decisions[field].astype("string")
        if values.isna().any() or values.str.strip().eq("").any() or values.ne(values.str.strip()).any():
            raise ValueError(f"missing or noncanonical identifier: {field}")
        decisions[field] = values
    if decisions.duplicated(["guild_id", "channel_id"]).any():
        raise ValueError("duplicate guild/channel pair")
    if decisions[["guild_name", "channel_name"]].isna().any().any():
        raise ValueError("guild_name and channel_name must not be missing")
    for field in ("total_messages", "distinct_human_authors"):
        values = pd.to_numeric(decisions[field], errors="raise")
        if pd.api.types.is_bool_dtype(values.dtype) or not np.isfinite(values).all() or (values < 0).any() or (values % 1 != 0).any():
            raise ValueError(f"{field} must contain finite nonnegative integer counts")
        decisions[field] = values.astype("int64")
    if decisions.distinct_human_authors.gt(decisions.total_messages).any():
        raise ValueError("distinct authors cannot exceed message records")
    decisions["manual_excluded"] = decisions.channel_name.isin(excluded_names)
    decisions["below_message_minimum"] = decisions.total_messages.lt(minimum_messages)
    decisions["below_author_minimum"] = decisions.distinct_human_authors.lt(minimum_human_authors)
    decisions["low_activity_excluded"] = decisions.below_message_minimum | decisions.below_author_minimum
    decisions["retained"] = ~(decisions.manual_excluded | decisions.low_activity_excluded)
    decisions["decision_reason"] = np.select(
        [decisions.manual_excluded & decisions.low_activity_excluded,
         decisions.manual_excluded, decisions.below_message_minimum & decisions.below_author_minimum,
         decisions.below_message_minimum, decisions.below_author_minimum],
        ["manual_and_activity", "manual_name", "messages_and_participants", "too_few_messages", "too_few_participants"],
        default="retained",
    )
    return decisions.sort_values(["guild_id", "channel_id"]).reset_index(drop=True)


def _read_names(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _statistics(connection: duckdb.DuckDBPyConnection, view: str) -> pd.DataFrame:
    return connection.execute(f"""
        SELECT cast(guild_id AS VARCHAR) AS guild_id, min(guild_name) AS guild_name,
               cast(channel_id AS VARCHAR) AS channel_id, min(channel_name) AS channel_name,
               count(*) AS total_messages,
               count(DISTINCT nullif(trim(cast(author_id AS VARCHAR)), ''))
                   FILTER (WHERE is_bot = false) AS distinct_human_authors
        FROM {view} GROUP BY guild_id, channel_id ORDER BY guild_id, channel_id
    """).fetchdf().astype({"guild_id": "string", "channel_id": "string"})


def _counts(decisions: pd.DataFrame) -> dict:
    return {
        "source_channels": len(decisions),
        "source_servers": int(decisions.guild_id.nunique()),
        "manual_excluded": int(decisions.manual_excluded.sum()),
        "below_message_minimum": int(decisions.below_message_minimum.sum()),
        "below_author_minimum": int(decisions.below_author_minimum.sum()),
        "low_activity_excluded": int(decisions.low_activity_excluded.sum()),
        "manual_activity_overlap": int((decisions.manual_excluded & decisions.low_activity_excluded).sum()),
        "excluded_channels": int((~decisions.retained).sum()),
        "retained_channels": int(decisions.retained.sum()),
        "retained_servers": int(decisions.loc[decisions.retained, "guild_id"].nunique()),
        "source_messages": int(decisions.total_messages.sum()),
        "removed_messages": int(decisions.loc[~decisions.retained, "total_messages"].sum()),
        "remaining_messages": int(decisions.loc[decisions.retained, "total_messages"].sum()),
    }


def select_channels(
    source: str | Path = DEFAULT_SOURCE,
    exclusions: str | Path = DEFAULT_EXCLUSIONS,
    output: str | Path = DEFAULT_OUTPUT,
    *,
    minimum_messages: int = 500,
    minimum_human_authors: int = 5,
    memory_limit: str = "2GB",
) -> dict:
    source, exclusions, output = (Path(path).resolve() for path in (source, exclusions, output))
    if output.exists():
        raise FileExistsError(f"selection output already exists: {output}")
    source_hash = sha256_file(source)
    exclusion_hash = sha256_file(exclusions)
    names = _read_names(exclusions)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".participants-", dir=output.parent) as temporary:
        staging = Path(temporary)
        work = staging / "work"
        work.mkdir()
        with duckdb.connect() as connection:
            connection.execute("SET memory_limit = ?", [memory_limit])
            connection.execute("SET threads = 2")
            connection.execute("SET temp_directory = ?", [str(work)])
            connection.execute("SET preserve_insertion_order = false")
            connection.from_parquet(str(source)).create_view("source")
            columns = {row[0] for row in connection.execute("DESCRIBE source").fetchall()}
            if missing := REQUIRED_COLUMNS - columns:
                raise ValueError(f"missing source columns: {', '.join(sorted(missing))}")
            statistics = _statistics(connection, "source")
            decisions = channel_decisions(statistics, names, minimum_messages=minimum_messages, minimum_human_authors=minimum_human_authors)
            unmatched = sorted(names - set(decisions.channel_name))
            if unmatched:
                raise ValueError(f"unmatched manual exclusion names: {unmatched}")
            kept = decisions.loc[decisions.retained, ["guild_id", "channel_id"]]
            connection.register("kept", kept)
            path = str(staging / "messages.parquet").replace("'", "''")
            connection.execute(f"""
                COPY (SELECT source.* FROM source JOIN kept
                    ON cast(source.guild_id AS VARCHAR) = kept.guild_id
                    AND cast(source.channel_id AS VARCHAR) = kept.channel_id)
                TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """)
            connection.from_parquet(str(staging / "messages.parquet")).create_view("retained")
            pd.testing.assert_frame_equal(
                _statistics(connection, "retained"),
                statistics.merge(kept, on=["guild_id", "channel_id"], validate="one_to_one").sort_values(["guild_id", "channel_id"]).reset_index(drop=True),
                check_dtype=False,
            )
        shutil.rmtree(work)
        statistics.to_parquet(staging / "channel_statistics.parquet", index=False)
        atomic_write_bytes(staging / "decisions.csv", decisions.to_csv(index=False, lineterminator="\n").encode("utf-8"))
        atomic_write_bytes(staging / "exclusions.txt", exclusions.read_bytes())
        manifest = {
            "manifest_schema_version": 2,
            "command": "select-channels-by-participants",
            "rule_version": RULE_VERSION,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "implementation_sha256": sha256_file(Path(__file__)),
            "inputs": [{"path": str(source), "sha256": source_hash, "immutable_source": True}, {"path": str(exclusions), "sha256": exclusion_hash, "immutable_source": True}],
            "parameters": {"minimum_messages": minimum_messages, "minimum_human_authors": minimum_human_authors, "low_activity_condition": "total_messages < minimum_messages OR distinct_human_authors < minimum_human_authors", "memory_limit": memory_limit},
            "definitions": {
                "total_messages": "all exported rows in the guild/channel, before payload or author filtering",
                "distinct_human_authors": "distinct nonblank trimmed author_id among rows with is_bot explicitly false; no reply, mention, payload or message-type condition",
                "unit": "guild_id/channel_id; no semantic conversation inference",
                "manual_exclusion": "exact channel_name match against stripped nonempty list entries; applies across servers",
            },
            "counts": _counts(decisions),
            "unmatched_manual_names": unmatched,
            "limitations": ["manual exclusion reasons are inherited and not recorded per channel", "500/5 are operational inclusion requirements, not statistically calibrated quality guarantees"],
            "source_data_policy": "read_only_immutable",
            "outputs": [{"name": filename, "sha256": sha256_file(staging / filename)} for filename in ("messages.parquet", "channel_statistics.parquet", "decisions.csv", "exclusions.txt")],
        }
        atomic_write_bytes(staging / "manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
        atomic_write_bytes(staging / "messages.parquet.manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
        staging.rename(output)
    return manifest


def verify_selection(directory: str | Path) -> dict:
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("rule_version") != RULE_VERSION:
        raise ValueError("unsupported participant selection rule")
    for item in manifest["outputs"]:
        if sha256_file(directory / item["name"]) != item["sha256"]:
            raise ValueError(f"hash mismatch: {item['name']}")
    if json.loads((directory / "messages.parquet.manifest.json").read_text(encoding="utf-8")) != manifest:
        raise ValueError("corpus manifest differs from selection manifest")
    parameters = manifest["parameters"]
    decisions = channel_decisions(pd.read_parquet(directory / "channel_statistics.parquet"), _read_names(directory / "exclusions.txt"), minimum_messages=parameters["minimum_messages"], minimum_human_authors=parameters["minimum_human_authors"])
    recorded = pd.read_csv(directory / "decisions.csv", dtype={"guild_id": "string", "channel_id": "string"}, keep_default_na=False)
    pd.testing.assert_frame_equal(recorded, decisions, check_dtype=False)
    if _counts(decisions) != manifest["counts"]:
        raise ValueError("manifest counts differ from recalculated decisions")
    with duckdb.connect() as connection:
        connection.from_parquet(str(directory / "messages.parquet")).create_view("retained")
        actual = _statistics(connection, "retained")
    fields = ["guild_id", "guild_name", "channel_id", "channel_name", "total_messages", "distinct_human_authors"]
    pd.testing.assert_frame_equal(actual, decisions.loc[decisions.retained, fields].reset_index(drop=True), check_dtype=False)
    return manifest["counts"]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Select software channels by message volume and distinct human participants.")
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select")
    select.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    select.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    select.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    select.add_argument("--minimum-messages", type=int, default=500)
    select.add_argument("--minimum-human-authors", type=int, default=5)
    select.add_argument("--memory-limit", default="2GB")
    verify = commands.add_parser("verify")
    verify.add_argument("directory", type=Path, nargs="?", default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)
    if arguments.command == "select":
        result = select_channels(arguments.source, arguments.exclusions, arguments.output, minimum_messages=arguments.minimum_messages, minimum_human_authors=arguments.minimum_human_authors, memory_limit=arguments.memory_limit)["counts"]
    else:
        result = verify_selection(arguments.directory)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()