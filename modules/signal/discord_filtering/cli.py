from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .profile import ProfileValidationError, load_profile
from .server_review import apply_server_review, prioritize_servers
from .service import (
    filter_servers,
    score_channels,
    write_channel_scoring_run,
    write_server_filtering_run,
)
from .storage import (
    OutputExistsError,
    sha256_file,
)


def _path(value: str) -> Path:
    return Path(value)


def _cmd_validate_profile(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    summary = {
        "valid": True,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "domain": profile.domain,
        "schema_version": profile.schema_version,
        "server_positive_rules": len(profile.server.positive_rules),
        "server_negative_rules": len(profile.server.negative_rules),
        "selection_defined": profile.server.selection is not None,
        "channel_scoring_defined": profile.channel is not None,
        "channel_positive_rules": len(profile.channel.positive_rules) if profile.channel else 0,
        "channel_negative_rules": len(profile.channel.negative_rules) if profile.channel else 0,
        "content_signals": len(profile.channel.signals) if profile.channel else 0,
        "sha256": sha256_file(args.profile),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _cmd_select_servers(args: argparse.Namespace) -> int:
    run = filter_servers(
        args.input,
        args.profile,
        include_rejected=args.include_rejected,
    )
    output, manifest_path = write_server_filtering_run(
        run,
        input_path=args.input,
        profile_path=args.profile,
        output_path=args.output,
        include_rejected=args.include_rejected,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "manifest": str(manifest_path.resolve()),
                "evaluated_servers": run.evaluated_servers,
                "selected_servers": run.selected_servers,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_score_channels(args: argparse.Namespace) -> int:
    run = score_channels(
        args.input,
        args.profile,
        min_messages=args.min_messages,
        guild_name=args.guild_name,
        guild_id=args.guild_id,
        all_guilds=args.all_guilds,
    )
    output, manifest_path = write_channel_scoring_run(
        run,
        input_path=args.input,
        profile_path=args.profile,
        output_path=args.output,
        min_messages=args.min_messages,
        guild_name=args.guild_name,
        guild_id=args.guild_id,
        all_guilds=args.all_guilds,
        overwrite=args.overwrite,
    )
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "manifest": str(manifest_path.resolve()),
                "source_rows_after_guild_filter": run.source_rows,
                "total_channels": len(run.records),
                "eligible_channels": run.eligible_channels,
                "insufficient_channels": run.insufficient_channels,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _cmd_server_review(args: argparse.Namespace) -> int:
    if args.command == "prioritize-servers":
        output, manifest = prioritize_servers(args.input, args.output)
    else:
        output, manifest = apply_server_review(args.input, args.review, args.output)
    print(json.dumps({"output": str(output.resolve()), "manifest": str(manifest.resolve())}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m discord_filtering",
        description="TangleTrace SIGNAL: auditable server and channel filtering using versioned external profiles.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-profile", help="validate a JSON profile without running filters")
    validate.add_argument("--profile", type=_path, required=True)
    validate.set_defaults(handler=_cmd_validate_profile)

    select = subparsers.add_parser("select-servers", help="classify server metadata (score only if selection is undefined)")
    select.add_argument("--profile", type=_path, required=True)
    select.add_argument("--input", type=_path, required=True)
    select.add_argument("--output", type=_path, required=True)
    select.add_argument(
        "--include-rejected",
        action="store_true",
        help="also emit rejected candidates for auditing/calibration",
    )
    select.add_argument("--overwrite", action="store_true")
    select.set_defaults(handler=_cmd_select_servers)

    prioritize = subparsers.add_parser("prioritize-servers", help="build a review queue using the upper Tukey fence of positive affinity scores")
    prioritize.add_argument("--input", type=_path, required=True)
    prioritize.add_argument("--output", type=_path, required=True)
    prioritize.set_defaults(handler=_cmd_server_review)

    review = subparsers.add_parser("apply-server-review", help="materialize accepted servers from an explicit accept/reject CSV")
    review.add_argument("--input", type=_path, required=True, help="candidate queue, not the full scored catalogue")
    review.add_argument("--review", type=_path, required=True)
    review.add_argument("--output", type=_path, required=True)
    review.set_defaults(handler=_cmd_server_review)

    score = subparsers.add_parser("score-channels", help="score channels from message Parquet")
    score.add_argument("--profile", type=_path, required=True)
    score.add_argument("--input", type=_path, required=True)
    score.add_argument("--output", type=_path, required=True)
    scope = score.add_mutually_exclusive_group(required=True)
    scope.add_argument("--guild-name", help="exact server name; use Neo4j for the pilot")
    scope.add_argument("--guild-id", help="exact server ID")
    scope.add_argument(
        "--all-guilds",
        action="store_true",
        help="explicitly load all servers (may require substantial memory)",
    )
    score.add_argument("--min-messages", type=int, default=50)
    score.add_argument("--overwrite", action="store_true")
    score.set_defaults(handler=_cmd_score_channels)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "min_messages") and args.min_messages < 1:
        parser.error("--min-messages must be >= 1")
    try:
        return int(args.handler(args))
    except (ProfileValidationError, OutputExistsError, OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
