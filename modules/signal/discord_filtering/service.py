from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .engine import classify_server, is_missing, score_channel
from .models import FilterProfile
from .profile import load_profile
from .storage import build_manifest, read_records, write_records_with_manifest


@dataclass(frozen=True, slots=True)
class ServerFilteringRun:
    """In-memory result of one profile-driven server filtering run."""

    profile: FilterProfile
    records: tuple[dict[str, Any], ...]
    evaluated_servers: int
    selected_servers: int


@dataclass(frozen=True, slots=True)
class ChannelScoringRun:
    """In-memory result of one profile-driven channel scoring run."""

    profile: FilterProfile
    records: tuple[dict[str, Any], ...]
    source_rows: int
    eligible_channels: int
    insufficient_channels: int


def assert_distinct_paths(input_path: str | Path, output_path: str | Path) -> None:
    source = Path(input_path)
    output = Path(output_path)
    if source.resolve() == output.resolve():
        raise ValueError(
            "input and output must be different paths; source datasets are immutable"
        )


def filter_servers(
    input_path: str | Path,
    profile_path: str | Path,
    *,
    include_rejected: bool = False,
) -> ServerFilteringRun:
    """Classify every input server with a versioned external profile."""

    profile = load_profile(profile_path)
    source_records = read_records(input_path)
    classifications = [classify_server(record, profile) for record in source_records]
    emitted = [
        result.to_record()
        for result in classifications
        if profile.server.selection is None or include_rejected or result.is_selected
    ]
    emitted.sort(
        key=lambda item: (
            -float(item["score_margin"]),
            -float(item["positive_score"]),
            float(item["negative_score"]),
            str(item["guild_id"]),
        )
    )
    return ServerFilteringRun(
        profile=profile,
        records=tuple(emitted),
        evaluated_servers=len(classifications),
        selected_servers=sum(bool(result.is_selected) for result in classifications),
    )


def write_server_filtering_run(
    run: ServerFilteringRun,
    *,
    input_path: str | Path,
    profile_path: str | Path,
    output_path: str | Path,
    include_rejected: bool,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Persist a server run atomically with a provenance manifest."""

    assert_distinct_paths(input_path, output_path)
    manifest = build_manifest(
        command="score-servers" if run.profile.server.selection is None else "select-servers",
        profile_path=profile_path,
        profile_id=run.profile.profile_id,
        profile_version=run.profile.profile_version,
        domain=run.profile.domain,
        input_paths=[input_path],
        parameters={
            "include_rejected": include_rejected,
            "selection_applied": run.profile.server.selection is not None,
        },
        counts={
            "evaluated_servers": run.evaluated_servers,
            "selected_servers": run.selected_servers,
            "emitted_rows": len(run.records),
        },
    )
    return write_records_with_manifest(
        run.records,
        output_path,
        manifest,
        overwrite=overwrite,
    )


def _load_message_frame(
    path: str | Path,
    *,
    guild_name: str | None,
    guild_id: str | None,
) -> Any:
    """Read an immutable source Parquet with optional guild predicate pushdown."""

    try:
        import pyarrow.parquet as pq
    except ImportError as error:  # pragma: no cover - project dependency guard
        raise RuntimeError(
            "score-channels requires the project's pyarrow dependency"
        ) from error

    source = Path(path)
    schema_names = set(pq.read_schema(source).names)
    required = {"channel_id", "channel_name", "content"}
    missing = sorted(required - schema_names)
    if missing:
        raise ValueError(f"{source}: missing required columns: {', '.join(missing)}")
    if guild_name is not None and "guild_name" not in schema_names:
        raise ValueError(f"{source}: guild_name filter requires column 'guild_name'")
    if guild_id is not None and "guild_id" not in schema_names:
        raise ValueError(f"{source}: guild_id filter requires column 'guild_id'")

    desired = [
        "guild_id",
        "guild_name",
        "channel_id",
        "channel_name",
        "channel_category",
        "channel_description",
        "topic",
        "message_id",
        "author_id",
        "author_username",
        "is_bot",
        "referenced_message_id",
        "mention_count",
        "timestamp",
        "content",
    ]
    columns = [column for column in desired if column in schema_names]
    filters: list[tuple[str, str, str]] = []
    if guild_name is not None:
        filters.append(("guild_name", "=", guild_name))
    if guild_id is not None:
        filters.append(("guild_id", "=", guild_id))
    return pq.read_table(source, columns=columns, filters=filters or None).to_pandas()


def _first_present(group: Any, column: str) -> Any:
    if column not in group.columns:
        return None
    for value in group[column]:
        if not is_missing(value):
            return value
    return None


def _channel_identity_record(group: Any) -> dict[str, Any]:
    return {
        "guild_id": _first_present(group, "guild_id"),
        "guild_name": _first_present(group, "guild_name"),
        "channel_id": _first_present(group, "channel_id"),
        "channel_name": _first_present(group, "channel_name"),
        "channel_category": _first_present(group, "channel_category"),
        "channel_description": _first_present(group, "channel_description"),
        "topic": _first_present(group, "topic"),
    }


def _score_message_frame(
    frame: Any,
    profile: FilterProfile,
    min_messages: int,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    group_columns = [
        column for column in ("guild_id", "channel_id") if column in frame.columns
    ]
    if "channel_id" not in group_columns:
        raise ValueError("message input must include channel_id")
    scored: list[dict[str, Any]] = []
    for _key, group in frame.groupby(group_columns, dropna=False, sort=False):
        message_columns = [
            column
            for column in (
                "message_id",
                "author_id",
                "author_username",
                "is_bot",
                "referenced_message_id",
                "mention_count",
                "timestamp",
                "content",
            )
            if column in group.columns
        ]
        result = score_channel(
            _channel_identity_record(group),
            profile,
            messages=group[message_columns].to_dict(orient="records"),
        )
        record = result.to_record()
        meets_min_messages = result.n_messages >= min_messages
        record["meets_min_messages"] = meets_min_messages
        record["eligibility_status"] = (
            "eligible" if meets_min_messages else "insufficient_data"
        )
        if not meets_min_messages:
            # Preserve the automatically estimated class/score for auditing,
            # but never promote a low-volume channel into the main analysis.
            record["include_in_main_analysis"] = False
            record["manual_review_required"] = True
        scored.append(record)
    scored.sort(
        key=lambda item: (
            -float(item["channel_score"]),
            -float(item["lexical_evidence_score"]),
            -int(item["n_messages"]),
            str(item["channel_id"]),
        )
    )
    return scored


def score_channels(
    input_path: str | Path,
    profile_path: str | Path,
    *,
    min_messages: int,
    guild_name: str | None = None,
    guild_id: str | None = None,
    all_guilds: bool = False,
) -> ChannelScoringRun:
    """Score channels with one profile and an explicit server scope."""

    if min_messages < 1:
        raise ValueError("min_messages must be >= 1")
    selected_scopes = sum(
        (guild_name is not None, guild_id is not None, bool(all_guilds))
    )
    if selected_scopes != 1:
        raise ValueError(
            "choose exactly one channel scope: guild_name, guild_id, or all_guilds=True"
        )
    profile = load_profile(profile_path)
    if profile.channel is None:
        raise ValueError("profile does not define a channel scoring policy")
    frame = _load_message_frame(
        input_path,
        guild_name=guild_name,
        guild_id=guild_id,
    )
    records = tuple(_score_message_frame(frame, profile, min_messages))
    eligible_channels = sum(bool(record["meets_min_messages"]) for record in records)
    return ChannelScoringRun(
        profile=profile,
        records=records,
        source_rows=len(frame),
        eligible_channels=eligible_channels,
        insufficient_channels=len(records) - eligible_channels,
    )


def write_channel_scoring_run(
    run: ChannelScoringRun,
    *,
    input_path: str | Path,
    profile_path: str | Path,
    output_path: str | Path,
    min_messages: int,
    guild_name: str | None,
    guild_id: str | None,
    all_guilds: bool,
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Persist a channel-scoring run atomically with a provenance manifest."""

    assert_distinct_paths(input_path, output_path)
    manifest = build_manifest(
        command="score-channels",
        profile_path=profile_path,
        profile_id=run.profile.profile_id,
        profile_version=run.profile.profile_version,
        domain=run.profile.domain,
        input_paths=[input_path],
        parameters={
            "guild_name": guild_name,
            "guild_id": guild_id,
            "all_guilds": all_guilds,
            "min_messages": min_messages,
            "exclude_bot_messages": run.profile.channel.exclude_bot_messages,
        },
        counts={
            "source_rows_after_guild_filter": run.source_rows,
            "total_channels": len(run.records),
            "eligible_channels": run.eligible_channels,
            "insufficient_channels": run.insufficient_channels,
        },
    )
    return write_records_with_manifest(
        run.records,
        output_path,
        manifest,
        overwrite=overwrite,
    )
