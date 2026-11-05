from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from discord_disentanglement.population import DEFAULT_OUTPUT, ROOT
from discord_filtering.storage import atomic_write_bytes, sha256_file


DEFAULT_REPORT = ROOT / "data/processed/disentanglement/reports/population.md"
INPUT_FILES = (
    "channels.csv", "servers.csv", "temporal_activity.csv",
    "reply_distances.csv", "concentration.csv", "summary.json",
)


def number(value: object, digits: int = 0) -> str:
    if value is None or pd.isna(value):
        return "NA"
    return f"{float(value):,.{digits}f}"


def percentage(numerator: float, denominator: float) -> str:
    return number(100 * numerator / denominator, 2) + "%" if denominator else "NA"


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def distribution(values: pd.Series) -> list[str]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return ["NA"] * 8
    return [number(value, 2) for value in (
        clean.min(), clean.quantile(0.25), clean.median(), clean.mean(),
        clean.quantile(0.75), clean.quantile(0.9), clean.quantile(0.95), clean.max(),
    )]


def concentration_statistics(volumes: pd.Series) -> dict:
    ordered = np.sort(volumes.to_numpy(dtype=float))[::-1]
    if (ordered < 0).any():
        raise ValueError("message volumes must be nonnegative")
    total = float(ordered.sum())
    if not total:
        return {"total": 0, "units": len(ordered), "gini": None, "hhi": None, "effective_units": None, "thresholds": [], "top_shares": []}
    shares = ordered / total
    cumulative = np.cumsum(ordered)
    ascending = ordered[::-1]
    ranks = np.arange(1, len(ordered) + 1)
    gini = float(2 * np.dot(ranks, ascending) / (len(ordered) * total) - (len(ordered) + 1) / len(ordered))
    hhi = float(np.square(shares).sum())
    thresholds = []
    for threshold in (0.5, 0.8, 0.9, 0.95):
        count = int(np.searchsorted(cumulative, threshold * total, side="left") + 1)
        thresholds.append({"threshold": threshold, "units": count, "actual_share": float(cumulative[count - 1] / total)})
    return {
        "total": total, "units": len(ordered), "gini": gini,
        "hhi": hhi, "effective_units": 1 / hhi, "thresholds": thresholds,
        "top_shares": [{"units": min(count, len(ordered)), "share": float(shares[:count].sum())} for count in (1, 5, 10, 20, 50)],
    }


def generate_population_report(
    input_dir: str | Path,
    output_path: str | Path,
    *,
    overwrite: bool = False,
) -> Path:
    directory = Path(input_dir).resolve()
    output = Path(output_path).resolve()
    provenance_path = output.with_name(output.name + ".manifest.json")
    if not overwrite and (output.exists() or provenance_path.exists()):
        raise FileExistsError(f"report already exists: {output}; use --overwrite")
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("usability_definition_version") != "payload_v2":
        raise ValueError("expected payload_v2 artifacts; rerun discord_disentanglement.population in a new directory")
    expected = {Path(item["path"]).name: item["sha256"] for item in manifest["outputs"]}
    hashes = {}
    for filename in INPUT_FILES:
        hashes[filename] = sha256_file(directory / filename)
        if expected.get(filename) != hashes[filename]:
            raise ValueError(f"artifact hash mismatch: {filename}")
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    channels = pd.read_csv(directory / "channels.csv", dtype={"guild_id": "string", "channel_id": "string"})
    servers = pd.read_csv(directory / "servers.csv", dtype={"guild_id": "string"})
    temporal = pd.read_csv(directory / "temporal_activity.csv", dtype={"period_utc": "string"})
    replies = pd.read_csv(directory / "reply_distances.csv", dtype={"guild_id": "string", "channel_id": "string"})
    concentration = pd.read_csv(directory / "concentration.csv")
    total = summary["total_records"]
    usable = summary.get("usable_human_messages", 0)
    if summary.get("usable_records", 0) + summary.get("unusable_records", 0) != total:
        raise ValueError("payload counts disagree with total records")
    for frame in (channels, servers):
        if frame["total_records"].sum() != total or frame["usable_human_messages"].sum() != usable:
            raise ValueError("aggregate counts disagree with summary")
        if frame["unusable_records"].sum() != summary.get("unusable_records", 0):
            raise ValueError("unusable counts disagree with summary")
    for unit in ("month", "weekday", "hour"):
        activity = temporal.loc[temporal.temporal_unit == unit]
        if activity.total_records.sum() != total - summary.get("missing_or_invalid_timestamp", 0):
            raise ValueError(f"temporal counts disagree: {unit}")
        if activity.usable_human_messages.sum() != usable - summary.get("usable_messages_without_valid_timestamp", 0):
            raise ValueError(f"usable temporal counts disagree: {unit}")
    if replies.replies.sum() + summary.get("native_replies_without_orderable_source", 0) != summary.get("native_reply_records", 0):
        raise ValueError("reply counts disagree with summary")
    lines = [
        "# Population characterization of retained channels",
        "## 1. Scope, sources and reproducibility",
        "This document describes the corpus after Stage 2 channel selection and before Stage 3 window sampling. Statistics describe the observed export, not all community messages, semantic classifications or toxicity outcomes.",
        f"Statistics extracted at: `{manifest['created_at_utc']}`. All timestamps and temporal groupings use UTC.",
        f"Frozen input: `{Path(manifest['inputs'][0]['path']).name}`.",
        "Calculations run in `discord_disentanglement/population_report.py` on CSVs and the summary produced by `discord_disentanglement/population.py`. The generator verifies artifact hashes and reconciles totals before writing; it does not reread millions of messages to generate this text.",
        "```powershell\npython -m discord_disentanglement.population_report\n```",
        "To regenerate explicitly or use other artifacts:",
        f"```powershell\npython -m discord_disentanglement.population_report `\n  --input-dir {DEFAULT_OUTPUT.relative_to(ROOT)} `\n  --output {DEFAULT_REPORT.relative_to(ROOT)} `\n  --overwrite\n```",
        "An adjacent manifest records hashes of the input artifacts, generator and Markdown. Hash validation covers the reports; this generator does not reread the source Parquet. Numbers use commas for thousands and a decimal point; NA indicates a zero denominator or unavailable measure. Rounding is presentation-only.",
        "## 2. Observed population and usable frame",
    ]
    overview = [
        ["Servers with records", number(len(servers))],
        ["Channels with records", number(len(channels))],
        ["Total records", number(total)],
        ["Explicitly human records", number(summary.get("human_records", 0))],
        ["Records with text or media (any author)", number(summary.get("usable_records", 0))],
        ["Usable human messages", number(usable)],
        ["Unusable: no recorded text or media", number(summary.get("unusable_records", 0))],
        ["Human messages with content and structural issues", number(summary.get("human_messages_with_structural_issues", 0))],
        ["Distinct human authors in the corpus", number(summary.get("distinct_human_authors", 0))],
        ["Distinct human authors in the usable frame", number(summary.get("distinct_usable_human_authors", 0))],
        ["First observed timestamp (UTC)", summary.get("first_timestamp_utc", "NA")],
        ["Last observed timestamp (UTC)", summary.get("last_timestamp_utc", "NA")],
        ["Days with observed corpus activity", number(summary.get("active_days", 0))],
    ]
    lines += [markdown_table(["Measure", "Value"], overview),
        "Unusable means only a record with neither nonblank text nor a recorded attachment, embed or sticker. Whitespace-only text is empty. Text or media makes a record usable here regardless of Discord type. A usable human message has recorded content and `is_bot = false`; missing bot status is not presumed human. Bots with content are not unusable, but do not belong to the human population.",
        "Missing IDs, invalid timestamps and duplicate keys are separate structural issues, not reasons for payload unusability. Records with content and these flags remain in usable volume; calculations requiring identity and chronological order exclude them from their specific base. All message types count when content exists. Usability does not guarantee topical relevance or annotation eligibility. The definitive sampling frame still requires review of window constraints.",
        "Authors are deduplicated globally by ID in the summary. Summing distinct authors per channel/server is not a global count because the same person can appear in several channels. Global active days are not sums of channel active days either.",
        f"Records with text or media represent {percentage(summary.get('usable_records', 0), total)} of the total; {percentage(summary.get('unusable_records', 0), total)} have no recorded content. Usable human messages represent {percentage(usable, total)} of the total. Among observed human authors, {percentage(summary.get('distinct_usable_human_authors', 0), summary.get('distinct_human_authors', 0))} have at least one usable message. The difference between observed and frame authors reflects content availability, not Discord type.",
        "The `payload_v2` definition replaces the initial rule that also rejected types other than 0/19 and structural issues. Earlier artifacts remain in `data/processed/disentanglement/population`; these statistics were recalculated with the new rule. Messages entirely absent from the export remain an unknown loss, distinct from present records without content.",
        "## 3. Volume distribution and concentration",
        "### 3.1. Distribution across channels and servers",
    ]
    distributions = []
    for scope, frame in (("Channel", channels), ("Server", servers)):
        for field, label in (("total_records", "Records"), ("usable_human_messages", "Usable messages"), ("distinct_human_authors", "Distinct human authors")):
            distributions.append([scope, label, *distribution(frame[field])])
    lines.append(markdown_table(["Unit", "Measure", "Min", "Q25", "Median", "Mean", "Q75", "Q90", "Q95", "Max"], distributions))
    lines.append("These quantiles are across units: each channel or server has weight one. They use linear interpolation (`pandas.Series.quantile`), not message-level quantiles.")
    lines.append("### 3.2. Cumulative concentration")
    concentration_rows = []
    concentration_indices = []
    top_rows = []
    for scope, frame in (("channel", channels), ("server", servers)):
        for population, field in (("all_records", "total_records"), ("usable_human", "usable_human_messages")):
            stats = concentration_statistics(frame[field])
            exported = concentration.loc[(concentration.scope == scope) & (concentration.population == population)]
            if exported.messages.sum() != stats["total"]:
                raise ValueError("concentration counts disagree")
            for item in stats["thresholds"]:
                concentration_rows.append([scope, population, percentage(item["threshold"], 1), number(item["units"]), percentage(item["units"], stats["units"]), percentage(item["actual_share"], 1)])
            concentration_indices.append([scope, population, number(stats["gini"], 4), number(stats["hhi"], 4), number(stats["effective_units"], 2)])
            for item in stats["top_shares"]:
                top_rows.append([scope, population, number(item["units"]), percentage(item["share"], 1)])
    lines += [markdown_table(["Unit", "Population", "Volume target", "Units required", "% of units", "Actual volume covered"], concentration_rows),
        "Units are ordered by descending volume. The threshold is the smallest number of units reaching the target; actual coverage can exceed it because channels are indivisible. `all_records` uses all records; `usable_human` uses the usable frame.",
        markdown_table(["Unit", "Population", "Gini", "HHI", "Effective units"], concentration_indices),
        "Gini measures volume inequality (0 means equal volumes). HHI is the sum of squared shares on a 0 to 1 scale; its inverse is the number of equal-volume units with equivalent concentration. These indices describe volume, not quality or scientific importance.",
        "$$G = \\frac{2\\sum_{i=1}^{k} i x_{(i)}}{k\\sum_{i=1}^{k}x_i}-\\frac{k+1}{k}, \\qquad HHI=\\sum_{i=1}^{k}s_i^2, \\qquad k_{effective}=\\frac{1}{HHI}$$",
        "In the Gini formula, volumes are sorted in ascending order; $s_i=x_i/\\sum_jx_j$.",
        markdown_table(["Unit", "Population", "Largest units", "% of messages"], top_rows),
        "### 3.3. Channel size bands",
    ]
    for label, frame in (("channels", channels), ("servers", servers)):
        stats = concentration_statistics(frame.usable_human_messages)
        if stats["total"]:
            threshold = next(item for item in stats["thresholds"] if item["threshold"] == 0.8)
            lines.insert(-1, f"In the usable population, {number(threshold['units'])} of {number(stats['units'])} {label} ({percentage(threshold['units'], stats['units'])}) reach 80% of volume, covering {percentage(threshold['actual_share'], 1)}. The largest unit accounts for {percentage(stats['top_shares'][0]['share'], 1)} of usable messages.")
    bins = [0, 500, 1000, 5000, 10000, 50000, 100000, float("inf")]
    labels = ["0 to 499", "500 to 999", "1,000 to 4,999", "5,000 to 9,999", "10,000 to 49,999", "50,000 to 99,999", "100,000 or more"]
    bands = pd.cut(channels.usable_human_messages, bins=bins, labels=labels, right=False)
    band_rows = []
    for label in labels:
        selected = channels.loc[bands == label]
        messages = selected.usable_human_messages.sum()
        band_rows.append([label, number(len(selected)), percentage(len(selected), len(channels)), number(messages), percentage(messages, usable)])
    lines += [markdown_table(["Usable messages per channel", "Channels", "% of channels", "Messages", "% of messages"], band_rows),
        "Bands use usable messages, not the raw volume used for channel selection. The current corpus requires at least 500 raw records and five distinct human authors per channel. A channel can have fewer than 500 usable messages if some records have no content.",
        "### 3.4. All servers by usable volume",
    ]
    ranked_servers = servers.sort_values(["usable_human_messages", "guild_id"], ascending=[False, True])
    lines.append(markdown_table(["Server", "guild_id", "Channels", "Records", "Usable", "% of frame", "Human authors", "First UTC", "Last UTC"], [
        [row.guild_name, row.guild_id, number(row.channels), number(row.total_records), number(row.usable_human_messages), percentage(row.usable_human_messages, usable), number(row.distinct_human_authors), row.first_timestamp_utc, row.last_timestamp_utc]
        for row in ranked_servers.itertuples()
    ]))
    ranked_channels = channels.sort_values(["usable_human_messages", "guild_id", "channel_id"], ascending=[False, True, True]).copy()
    ranked_channels["cumulative_messages"] = ranked_channels.usable_human_messages.cumsum()
    lines.append("### 3.5. Top 20 channels by usable volume")
    lines.append(markdown_table(["Server", "Channel", "channel_id", "Usable", "% of frame", "Cumulative %", "Human authors"], [
        [row.guild_name, row.channel_name, row.channel_id, number(row.usable_human_messages), percentage(row.usable_human_messages, usable), percentage(row.cumulative_messages, usable), number(row.distinct_human_authors)]
        for row in ranked_channels.head(20).itertuples()
    ]))
    lines += ["## 4. Authors and participation",
        "`distinct_human_authors` counts distinct human IDs in the channel without requiring replies or mentions. `distinct_usable_human_authors` requires at least one message with recorded content. Both count participants, not inferred semantic conversations. Selection uses the first count and raw channel volume.",
        markdown_table(["Measure per channel", "Min", "Q25", "Median", "Mean", "Q75", "Q90", "Q95", "Max"], [
            [field, *distribution(channels[field])] for field in ("distinct_human_authors", "distinct_usable_human_authors")
        ]),
        "The current rule excludes a channel when `total_messages < 500 OR distinct_human_authors < 5`, in addition to manual exclusions. Both counts come directly from original messages. Selection, characterization and sampling were versioned again; earlier results do not define the current frame. See `reproducibility/03-channel-selection.md` for the protocol.",
        "Aggregated artifacts contain no per-author counts; this document therefore does not estimate individual productivity, dominant-author share or concentration across authors.",
        "## 5. Temporal coverage and distribution",
        "### 5.1. Coverage per channel",
    ]
    first = pd.to_datetime(channels.first_timestamp_utc, utc=True, format="mixed")
    last = pd.to_datetime(channels.last_timestamp_utc, utc=True, format="mixed")
    spans = (last.dt.normalize() - first.dt.normalize()).dt.days + 1
    rates = channels.usable_human_messages / channels.usable_active_days.replace(0, np.nan)
    lines += [markdown_table(["Measure per channel", "Min", "Q25", "Median", "Mean", "Q75", "Q90", "Q95", "Max"], [
        ["Calendar-day span (inclusive)", *distribution(spans)],
        ["Active days (all records)", *distribution(channels.active_days)],
        ["Active days (usable frame)", *distribution(channels.usable_active_days)],
        ["Usable messages per active day", *distribution(rates)],
    ]),
        "Span is the difference between extreme UTC dates plus one day; it does not guarantee continuous collection. Messages per active day divides usable volume by days with at least one usable channel message. It is not a calendar-day average or export-availability-adjusted intensity.",
        "### 5.2. Activity by year",
    ]
    months = temporal.loc[temporal.temporal_unit == "month"].copy()
    months["year"] = months.period_utc.str[:4]
    years = months.groupby("year")[["total_records", "usable_human_messages"]].sum()
    lines.append(markdown_table(["UTC year", "Records", "% of records", "Usable", "% of frame"], [
        [year, number(row.total_records), percentage(row.total_records, total), number(row.usable_human_messages), percentage(row.usable_human_messages, usable)] for year, row in years.iterrows()
    ]))
    lines.append("Boundary years and months may be partial. Annual counts are not annualized rates; differences may reflect export coverage, channels entering/leaving or actual activity changes.")
    lines.append("### 5.3. Top ten months by usable volume")
    monthly = months.groupby("period_utc")[["total_records", "usable_human_messages"]].sum().reset_index()
    monthly = monthly.sort_values(["usable_human_messages", "period_utc"], ascending=[False, True])
    lines.append(markdown_table(["UTC month", "Records", "Usable", "% of frame"], [
        [row.period_utc, number(row.total_records), number(row.usable_human_messages), percentage(row.usable_human_messages, usable)] for row in monthly.head(10).itertuples()
    ]))
    for unit, title, index, names in (
        ("weekday", "5.4. Activity by weekday", range(1, 8), ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]),
        ("hour", "5.5. Activity by UTC hour", range(24), [f"{hour:02d}:00 to {hour:02d}:59" for hour in range(24)]),
    ):
        selected = temporal.loc[temporal.temporal_unit == unit].copy()
        selected["bucket"] = selected.period_utc.astype(int)
        buckets = selected.groupby("bucket")[["total_records", "usable_human_messages"]].sum().reindex(index, fill_value=0)
        lines.append(f"### {title}")
        lines.append(markdown_table(["UTC period", "Records", "Usable", "% of frame"], [
            [label, number(row.total_records), number(row.usable_human_messages), percentage(row.usable_human_messages, usable)] for label, row in zip(names, buckets.itertuples())
        ]))
    lines += ["Weekdays and hours aggregate all periods and channels. Shares are not adjusted for occurrences of each weekday or participants' local time zones. Only observed buckets are exported; missing weekday/hour buckets are filled with zero here without assuming complete collection. Missing/invalid timestamps cannot be grouped temporally even when content exists; shares use total volume as denominator.",
        "## 6. Native replies, parents and distances",
        "### 6.1. Frequency and denominators",
        markdown_table(["Measure", "Count", "Denominator", "Share"], [
            ["Native replies", number(summary.get("native_reply_records", 0)), "All records", percentage(summary.get("native_reply_records", 0), total)],
            ["Usable native replies", number(summary.get("usable_native_replies", 0)), "Usable messages", percentage(summary.get("usable_native_replies", 0), usable)],
            ["Any native reference", number(summary.get("reference_records", 0)), "All records", percentage(summary.get("reference_records", 0), total)],
            ["Reply without parent ID", number(summary.get("replies_without_parent_id", 0)), "All records", percentage(summary.get("replies_without_parent_id", 0), total)],
        ]),
        "A native reply requires Discord type 19 and a nonblank reference ID. References of other types do not count as replies. Absence of a native reply does not imply absence of a semantic response.",
        "### 6.2. Parent resolution",
    ]
    status_rows = []
    for population, frame in (("All orderable sources", replies), ("Usable sources", replies.loc[replies.source_usable == True])):
        denominator = frame.replies.sum()
        for status, count in frame.groupby("status").replies.sum().items():
            status_rows.append([population, status, number(count), number(denominator), percentage(count, denominator)])
    lines += [markdown_table(["Reply population", "Status", "Replies", "Denominator", "Share"], status_rows),
        f"Replies with unorderable sources, outside the distance table: {number(summary.get('native_replies_without_orderable_source', 0))}.",
        "`resolved`: unique identified parent with a valid timestamp, preceding the source in the same channel; `parent_not_found`: absent from the orderable base; `different_channel`: found in another channel; `not_preceding`: self-reference or a later parent. Not found does not prove exclusion: the message may be outside the export or unorderable.",
        "### 6.3. Aggregate positional reach",
    ]
    distance_rows = []
    for population, frame in (("All sources", replies), ("Usable sources", replies.loc[replies.source_usable == True])):
        resolved = frame.loc[frame.status == "resolved"]
        denominator = resolved.replies.sum()
        for threshold in (10, 100, 200):
            count = resolved[f"within_{threshold}_records"].sum()
            distance_rows.append([population, number(threshold), number(count), number(denominator), percentage(count, denominator)])
        pairs = resolved.usable_parent_pairs.sum()
        lines.append(f"{population}: {number(pairs)} usable source/parent pairs among {number(denominator)} resolved replies ({percentage(pairs, denominator)}).")
    lines += [markdown_table(["Population", "Distance up to (records)", "Covered replies", "Resolved replies", "Coverage"], distance_rows),
        "Global shares divide summed channel counts by summed resolved replies, not the mean of shares. Distance is source position minus parent position; 1 means adjacency. Order includes all unique identifiable records with valid timestamps, including bots and system types. An alternative usable-message order is available for usable pairs.",
        "Coverage within 200 records diagnoses native reply reach, not sufficient context for semantic edges. Target position within the window and the ordering used for windows also affect available context.",
        "### 6.4. Quantiles for high-volume channels",
    ]
    quantile_rows = []
    available = replies.loc[(replies.status == "resolved") & (replies.source_usable == True)]
    lookup = {(row.guild_id, row.channel_id): row for row in available.itertuples()}
    for channel in ranked_channels.head(20).itertuples():
        row = lookup.get((channel.guild_id, channel.channel_id))
        if row is None:
            continue
        positions = json.loads(row.position_quantiles)
        seconds = json.loads(row.seconds_quantiles)
        quantile_rows.append([channel.guild_name, channel.channel_name, channel.channel_id, number(row.replies), number(positions[1], 2), number(positions[4], 2), number(seconds[1] / 60, 2), number(seconds[4] / 3600, 2)])
    lines += [markdown_table(["Server", "Channel", "channel_id", "Usable resolved replies", "Positional median", "Positional Q95", "Time median (min)", "Time Q95 (h)"], quantile_rows),
        "Quantiles use resolved replies with usable sources in each channel. Parents may not be usable. Minutes and hours divide seconds by 60 and 3,600. The source CSV preserves Q25, Q50, Q75, Q90, Q95 and Q99, including the alternative usable order. Exact global quantiles cannot be recovered from channel quantiles alone; this document neither invents them nor averages quantiles.",
        "## 7. Bots, missing fields and unusable records",
    ]
    quality_fields = (
        ("bot_records", "Recorded bots"), ("unknown_bot_status", "Missing bot status"),
        ("missing_message_id", "Missing message ID"), ("missing_author_id", "Missing author ID"),
        ("missing_scope", "Missing server/channel"), ("missing_or_invalid_timestamp", "Missing/invalid timestamp"),
        ("duplicate_id_records", "Records with duplicate keys"), ("empty_text_records", "Empty or missing text"),
        ("human_messages_with_structural_issues", "Human messages with content and structural issues"),
        ("other_or_unknown_type_records", "Type other than 0/19 or missing (does not imply unusability)"),
        ("unusable_records", "Unusable: no recorded text or media"),
    )
    lines += [markdown_table(["Flag", "Records", "% of all records"], [
        [label, number(summary.get(field, 0)), percentage(summary.get(field, 0), total)] for field, label in quality_fields
    ]),
        "Flags are descriptive, may overlap and must not be summed. Only simultaneous absence of text and media defines unusability. Other types, bots and structural issues do not count as unusable merely because they have those characteristics. Empty text is not enough when an attachment, embed or sticker exists. Recorded media does not imply its content was downloaded or will be visible to annotators.",
        "Zero bots describes only the analyzed input, which may already exclude bots. It does not show that servers have no bots. Messages entirely absent from the export cannot be counted without an external source; missing parents and fields are different indicators from this unknown loss.",
        "## 8. Implications for window construction",
        "Evaluate concentration on `usable_human` when planning targets. Volume-proportional sampling favors large channels: appropriate for a message-level mean, but potentially leaving few small-channel examples for comparisons. Channel-level and message-level means are distinct estimands.",
        "One alternative is minimum channel coverage with the remainder proportional to volume. Record inclusion probabilities and weights when defining the design. This characterization neither determines sample size nor estimates design effects or draws windows.",
        "Temporal stratification within channels avoids selecting only history boundaries or highest-activity months. Global yearly volume must not replace assessment of each channel's available period. Periods without records prove neither inactivity nor collection failure.",
        "The human pilot should compare native reply positional reach with annotated semantic parents, record out-of-context cases and inspect media messages. Do not treat absence of native replies as negative labels or participant counts as complete measures of sociability.",
        "## 9. Complete channel inventory",
        "One row per `(guild_id, channel_id)`, ordered by usable volume. H authors are distinct humans; U authors have usable messages. Replies % divides usable native replies by usable channel messages. Detailed flags and additional quantiles remain in CSVs.",
        markdown_table(["Server", "guild_id", "Channel", "channel_id", "Records", "Usable", "% of frame", "H authors", "U authors", "Replies %", "U active days", "First UTC", "Last UTC"], [
            [row.guild_name, row.guild_id, row.channel_name, row.channel_id, number(row.total_records), number(row.usable_human_messages), percentage(row.usable_human_messages, usable), number(row.distinct_human_authors), number(row.distinct_usable_human_authors), percentage(row.usable_native_replies, row.usable_human_messages), number(row.usable_active_days), row.first_timestamp_utc, row.last_timestamp_utc]
            for row in ranked_channels.itertuples()
        ]),
        "## 10. Auditable sources",
        "Input files are in `" + directory.relative_to(ROOT).as_posix() + "`." if directory.is_relative_to(ROOT) else f"Artifact directory: `{directory}`.",
        markdown_table(["File", "SHA-256"], [[filename, f"`{hashes[filename]}`"] for filename in INPUT_FILES]),
        "Numerators, denominators, groupings, bands and additional formulas are in the Python generator. Original extraction definitions and Parquet provenance are in the population manifest. No manual calculations were added outside these executable files.",
    ]
    payload = ("\n\n".join(lines) + "\n").encode("utf-8")
    atomic_write_bytes(output, payload, overwrite=overwrite)
    provenance = {
        "manifest_schema_version": 1,
        "command": "generate-population-report",
        "generator_sha256": sha256_file(Path(__file__)),
        "population_manifest_sha256": sha256_file(directory / "manifest.json"),
        "inputs": [{"path": str(directory / filename), "sha256": hashes[filename]} for filename in INPUT_FILES],
        "output": {"path": str(output), "sha256": sha256_file(output)},
    }
    atomic_write_bytes(provenance_path, json.dumps(provenance, indent=2).encode() + b"\n", overwrite=overwrite)
    return output


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate an auditable detailed population report in Markdown.")
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args(argv)
    print(generate_population_report(arguments.input_dir, arguments.output, overwrite=arguments.overwrite))


if __name__ == "__main__":
    main()