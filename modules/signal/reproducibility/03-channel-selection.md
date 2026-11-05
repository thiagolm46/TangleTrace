# 3. Current Channel Selection

[Previous: servers](02-server-filtering.md) | [Next: optional scoring](04-channel-scoring.md)

## Rule

For each `(guild_id, channel_id)`, retain all its source rows if:

```text
total_messages >= 500
AND distinct_human_authors >= 5
AND channel_name is not in the manual exclusion list
```

The inverse activity condition is OR: exclude if either minimum fails.
Exactly **500 records and 5 human authors pass**.
No reply, mention, inferred conversation or semantic score is required.

Definitions implemented by [channel_selection.py](../discord_filtering/channel_selection.py):

- `total_messages`: all source rows for that server/channel, before payload,
  author or message-type filtering **at this stage**. If extraction already
  excluded bots, this does not restore them. It is not a deduplicated count.
- `distinct_human_authors`: distinct nonblank, trimmed string `author_id`
  values on rows with `is_bot` explicitly false. Null bot status is not human.
  Content, Discord type, replies and mentions do not affect this count.
- Manual exclusion: exact, **case-sensitive** `channel_name` match against
  nonempty stripped UTF-8 lines. The same name in different servers excludes
  every matching channel.

The checked-in [exclusion list](../configs/filtering/channel_exclusions.v1.txt)
preserves the original names, emoji and scripts. Translating these would
change the selected population. It reproduces inherited decisions whose
individual rationales were not recorded. It is not an English-language-only
corpus filter or a general-purpose language detector.

## Run and Verify

```powershell
uv run --locked python -m discord_filtering.channel_selection select `
  --source "$Run\messages.parquet" `
  --exclusions $Exclusions `
  --output "$Run\participants" `
  --minimum-messages 500 `
  --minimum-human-authors 5 `
  --memory-limit 2GB
if ($LASTEXITCODE -ne 0) { throw "Channel selection failed." }
uv run --locked python -m discord_filtering.channel_selection verify `
  "$Run\participants"
if ($LASTEXITCODE -ne 0) { throw "Selection verification failed." }
```

Required source columns:
`guild_id`, `guild_name`, `channel_id`, `channel_name`, `author_id`, `is_bot`.
Use canonical string IDs. Missing columns, nonpositive thresholds, invalid
statistics and exclusion names not found in the source fail explicitly.
For a different corpus, supply a new exclusion file rather than suppressing
unmatched-name errors. An empty UTF-8 file explicitly means no manual names.

The command recounts the original source, not a legacy statistics table.
It stages the run in a temporary directory, recounts the output, verifies
agreement, then publishes to a new directory. It never replaces an existing
selection directory.

## Output Contract

| Artifact inside the output directory | Meaning |
| --- | --- |
| `messages.parquet` | All original columns and rows of retained channels |
| `channel_statistics.parquet` | Source counts for every channel |
| `decisions.csv` | Counts, exclusion flags, retained flag and reason |
| `exclusions.txt` | Exact copy of the supplied exclusion file |
| `manifest.json` | Definitions, counts, parameters, hashes and limitations |
| `messages.parquet.manifest.json` | Identical manifest beside the corpus |

Rule version: `participants_min500_min5.v2`.
Decision reasons are `retained`, `manual_name`, `too_few_messages`,
`too_few_participants`, `messages_and_participants` or `manual_and_activity`.
Flags may overlap; never sum them as disjoint categories.

`verify` checks output hashes, both manifest copies, decisions recalculated
from saved statistics, manifest counts and actual retained-corpus statistics.
It does not reread or hash the original source path during verification.
To prove the entire transformation again, run `select` from the frozen source
into another new directory, then compare keyed statistics and decisions.

## Historical Reference Results

| Measure | Count |
| --- | ---: |
| Source servers / channels | 31 / 689 |
| Source records | 13,275,074 |
| Channels matching manual names | 66 |
| Below 500 records | 335 |
| Below 5 human authors | 177 |
| Below either activity minimum | 335 |
| Manual/activity overlap | 9 |
| Excluded channels (union) | 392 |
| Retained channels / servers | 297 / 29 |
| Removed records | 1,377,215 |
| Retained records | 11,897,859 |

These are exact counts for the historical extracted source. A source
snapshot, bot policy or review change can legitimately change them.
500/5 are operational inclusion requirements, not calibrated evidence of
technical relevance, representativeness or semantic conversation quality.
Two accepted servers have no retained channels; server counts therefore
decrease from 31 to 29 without changing the server review decisions.
