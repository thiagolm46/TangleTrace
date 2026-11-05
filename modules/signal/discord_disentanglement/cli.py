from __future__ import annotations

import argparse
from pathlib import Path

from discord_disentanglement import population, population_report, sampling, sampling_audit
from discord_disentanglement.annotation_bundle import build_annotation_bundle, publish_annotation_dataset


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TangleTrace SIGNAL: software-engineering data preparation; no model training or inference."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for command, description in (
        ("population", "Characterize retained channels."),
        ("population-report", "Generate the detailed population Markdown."),
        ("prepare-frame", "Create the channel eligibility register for review."),
        ("draw", "Select probabilistic message windows."),
        ("audit-sampling", "Audit the frozen sample without redrawing."),
    ):
        commands.add_parser(command, help=description, add_help=False)
    bundle = commands.add_parser("build-annotation-bundle", help="Flatten sampled windows into annotation tables.")
    bundle.add_argument("--annotation-windows", type=Path, required=True)
    bundle.add_argument("--output", type=Path, required=True)
    publish = commands.add_parser("publish-annotation-dataset", help="Publish annotation tables, codebook and native silver evidence.")
    publish.add_argument("--bundle-dir", type=Path, required=True)
    publish.add_argument("--native-reply-edges", type=Path, required=True)
    publish.add_argument("--codebook", type=Path, required=True)
    publish.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    arguments, remaining = parser.parse_known_args(argv)
    if arguments.command == "population":
        population.main(remaining)
    elif arguments.command == "population-report":
        population_report.main(remaining)
    elif arguments.command in {"prepare-frame", "draw"}:
        sampling.main([arguments.command, *remaining])
    elif arguments.command == "audit-sampling":
        sampling_audit.main(remaining)
    else:
        if remaining:
            parser.error(f"unrecognized arguments: {' '.join(remaining)}")
        if arguments.command == "build-annotation-bundle":
            result = build_annotation_bundle(arguments.annotation_windows, arguments.output)
            print(result.messages_path)
        else:
            published = publish_annotation_dataset(arguments.bundle_dir, arguments.native_reply_edges, arguments.codebook, arguments.output)
            print(published.manifest_path)