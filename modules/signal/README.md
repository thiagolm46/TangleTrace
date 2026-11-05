# TangleTrace SIGNAL

**Corpus Preparation & Sampling** (`tangletrace-signal`)

**TangleTrace: An Auditable Workbench for Discord Conversation Annotation**

TangleTrace combines SIGNAL with **TangleTrace BETWEEN**
(`tangletrace-between`), the **Reply-Link Annotation & Review** application.
This module lives in `modules/signal` in the unified
[TangleTrace repository](../../README.md); BETWEEN lives in the sibling
`modules/between`. Both modules retain independent packaging and execution.
SIGNAL was previously called Toxicity-OSS.

SIGNAL is an auditable, profile-driven pipeline for filtering **Discord Unveiled**
into a software engineering corpus. It covers server scoring, explicit human
server review, message extraction, channel scoring and channel selection.
Optional stages characterize the retained population and prepare samples
for annotation in BETWEEN.

**Start with the [English reproducibility guide](reproducibility/README.md).**
It includes executable PowerShell commands, input/output contracts, scoring
formulas, recorded review decisions, verification steps and limitations.
The existing [research documentation](docs/methodology) is preserved in its
original language; it is not the English reproduction manual.

## Installation

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/), and enough disk
space for the chosen data acquisition route.

Run the commands below from `modules/signal`.

```powershell
uv sync --locked
uv run --locked python -m discord_filtering --help
uv run --locked python -m discord_data --help
uv run --locked python -m discord_disentanglement --help
```

The Python distribution is named `tangletrace-signal`; its existing entry
points remain `discord-data`, `discord-filter` and `discord-prepare`.
Examples use module commands through `uv run --locked` so virtual-environment
activation is unnecessary.

## Pipeline

| Stage | Implementation | Reproduction instructions |
| --- | --- | --- |
| Acquire metadata and archive | [discord_data](discord_data/cli.py) | [Setup and sources](reproducibility/01-setup-and-sources.md) |
| Score, prioritize and review servers | [Filtering CLI](discord_filtering/cli.py), [review](discord_filtering/server_review.py) | [Server filtering](reproducibility/02-server-filtering.md) |
| Extract accepted servers | [Extraction](discord_data/extraction.py) | [Server filtering](reproducibility/02-server-filtering.md#3-extract-messages-for-accepted-servers) |
| Select channels by volume and participants | [Channel selection](discord_filtering/channel_selection.py) | [Channel selection](reproducibility/03-channel-selection.md) |
| Optional profile-based channel scoring | [Scoring engine](discord_filtering/engine.py) | [Channel scoring](reproducibility/04-channel-scoring.md) |
| Characterize, sample, audit and prepare annotation | [Preparation CLI](discord_disentanglement/cli.py) | [Downstream preparation](reproducibility/05-validation-and-preparation.md) |

The current server profile is **scoring-only**: it does not automatically
accept servers and does not define channel scoring. The separate A-D channel
scorer is supported, but **did not produce the current retained corpus**.
That corpus uses the explicit volume/participant rule below.

## Handoff to BETWEEN

A sample contains `sampled_messages.parquet`, `selected_windows.csv` and
`annotation_windows.csv`. BETWEEN can import the sample directory containing
the first two files or the windows CSV. The canonical annotation bundle is a
separate interchange output, not BETWEEN's direct import format. See
[downstream preparation](reproducibility/05-validation-and-preparation.md)
for the sampling and handoff steps.

## Current Selection Rule

Keep a channel only if all three conditions hold:

1. At least **500 exported message records**.
2. At least **5 distinct human author IDs**.
3. Its exact name is absent from the versioned manual exclusion list.

The unit is `(guild_id, channel_id)`. Replies, mentions and inferred
conversations are not prerequisites. These are operational thresholds,
not statistically calibrated guarantees of relevance or conversation quality.

The historical reference run contains **31 accepted servers** before channel
selection and **29 servers, 297 channels and 11,897,859 records** afterwards.
These counts apply to the frozen historical inputs, not arbitrary future
versions of the upstream dataset.

The repository versions the [server decisions](configs/filtering/server_review.v1.csv)
and [channel exclusions](configs/filtering/channel_exclusions.v1.txt).
Raw messages and generated corpora are not distributed in Git.
Access and redistribution must comply with the upstream dataset's terms.
Source text, server/channel names and multilingual matching patterns are
preserved verbatim: translating them would change the filter's meaning.

## Verification

```powershell
uv run --locked python -m pytest tests -q
```

After running the selection workflow with a new output directory:

```powershell
uv run --locked python -m discord_filtering.channel_selection verify `
  data\processed\reproduction\run_001\participants
```

Filtering outputs include SHA-256 provenance manifests. Existing artifacts
are protected from replacement by default. Keep each run in a new directory;
do not overwrite historical inputs or outputs.

## Scope and Maintenance

The repository does not train or run disentanglement or toxicity models,
ship model checkpoints, or claim a completed human-annotated benchmark.
Native replies are observed silver evidence; their absence is not a negative
semantic label. The internal package name `discord_disentanglement` remains
for import and provenance compatibility.

Population and sampling reports are now generated in
`data\processed\disentanglement\reports` by default, not in the preserved
research documentation. Report text and numeric formatting are English.

Legacy cleanup is a dry run unless explicitly applied:

```powershell
uv run --locked python scripts\cleanup_legacy.py
uv run --locked python scripts\cleanup_legacy.py --apply `
  --report data\maintenance\legacy_cleanup.json
```

The script uses a closed list of legacy paths and checks references in
preserved manifests. Current corpora, historical annotation packages,
research notes, the paper and the active audit are not deletion targets.
