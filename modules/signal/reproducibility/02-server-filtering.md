# 2. Server Scoring, Review and Extraction

[Previous: sources](01-setup-and-sources.md) | [Next: channels](03-channel-selection.md)

## 1. Score the Metadata Catalogue

```powershell
uv run --locked python -m discord_filtering validate-profile --profile $ServerProfile
uv run --locked python -m discord_filtering select-servers `
  --profile $ServerProfile `
  --input "$Raw\servers_metadata.txt" `
  --output "$Run\servers_scored.parquet"
```

The command is named `select-servers` for compatibility. With
[software.engineering.v2.json](../configs/filtering/software.engineering.v2.json),
it **scores every server**: there is no `server.selection` policy.
The manifest reports `selection_applied: false`, `selected_servers: 0`
and command `score-servers`. Zero selected here does not mean zero candidates.

Input metadata uses `id` or `guild_id` plus the configured text fields.
The reader supports JSON arrays (`.json`/`.txt`), JSONL, CSV and Parquet.
Keep Discord IDs as strings, never floating-point numbers.
Output contains identity, positive/negative scores, net affinity,
matched evidence and metadata availability. The
[models](../discord_filtering/models.py) define the complete record schema.

### Scoring formula

Profile identity: `software-engineering-server-scoring`, version `2.2.0`,
schema `2`, domain `software`.

| Metadata field | Multiplier |
| --- | ---: |
| `name` | 1.50 |
| `description` | 1.25 |
| `about` | 1.00 |
| `reasons_to_join` | 1.00 |
| `keywords` | 1.00 |

Text is normalized with Unicode NFKC; regex matching is case-insensitive.
Keywords can be a list or a scalar string. Missing and empty values provide
no evidence. Multilingual regex alternatives are intentional.

For each polarity (positive and negative), independently:

1. Find each rule's first match in each field value.
2. Compute `rule.weight * field_weight`.
3. Within each semantic group, credit only the largest adjusted weight
   (`max_per_group`).
4. Add **0.5** for each additional distinct matching field beyond the winning
   field, capped at **1.0 per group**. Repeating terms within a field does not
   multiply its score.
5. Sum credited group contributions, rounded to six decimal places.

Let `P` and `N` be positive and negative totals. Affinity is `A = P - N`,
also exposed as `software_affinity_score`. It is a heuristic index, **not
a probability**. For example, one weight-5 group matching `name` and
`description` receives `5 * 1.5 + 0.5 = 8.0`, not `7.5 + 6.25`.

Groups cover explicit software intent, developer communities, open source,
engineering practices, specializations, artifacts, languages, data platforms
and infrastructure. Negative groups provide adult-content, finance, gaming,
dating and promotional evidence. Negative evidence does not independently
reject a server in this scoring-only profile.

The [engine](../discord_filtering/engine.py) preserves every match's rule,
field, matched text, offsets, adjusted weight and credited weight.

## 2. Build the Queue and Replay Human Review

```powershell
uv run --locked python -m discord_filtering prioritize-servers `
  --input "$Run\servers_scored.parquet" `
  --output "$Run\server_candidates.parquet"
uv run --locked python -m discord_filtering apply-server-review `
  --input "$Run\server_candidates.parquet" `
  --review $Review `
  --output "$Run\manual_selected_servers.parquet"
```

The prioritizer calculates Q1/Q3 by **linear interpolation among strictly
positive affinities only**. It keeps servers strictly above
`Q3 + 1.5 * (Q3 - Q1)`. It records the quartiles and fence in a manifest.
This reconstructs the historical inspection queue; it is not an empirically
validated universal domain threshold.

Historical reference:

| Quantity | Value |
| --- | ---: |
| Scored servers | 3,167 |
| Strictly positive scores | 282 |
| Q1 / Q3 | 3.00 / 5.25 |
| IQR / upper fence | 2.25 / 8.625 |
| Candidates above the fence | 37 |
| Accepted / rejected by recorded review | 31 / 6 |

The versioned [review CSV](../configs/filtering/server_review.v1.csv) uses:

```csv
guild_id,decision
698610475432411196,accept
278017358692352000,reject
```

Only exact `accept` and `reject` are valid. Each candidate must appear exactly
once, with no extra IDs. Missing decisions, duplicates and mismatched input
queues fail explicitly. The output contains accepted servers only, with
`is_selected=true`, `manual_decision=accept` and the original scored metadata.
The extraction loader therefore has both IDs and server names.

The table incorporates the recorded correction rejecting Firebelly Studios
(`135844298527735818`). Do not restore its earlier accepted status.
Per-server reasons were not preserved; do not infer them from names or scores.

For a different source snapshot, a queue mismatch is expected: conduct a
new scoped review and save a new CSV. The historical table cannot approve
unseen candidates. Human validity means software development, maintenance,
tools or practices are central to the community, not merely mentioned.
Hybrid game-development/modding communities can qualify; game mentions alone
are not sufficient. Record date, reviewer protocol and individual rationales
for new reviews, without modifying historical decisions.

## 3. Extract Messages for Accepted Servers

Recommended frozen local route:

```powershell
uv run --locked python -m discord_data extract-local `
  --dataset-path "$Raw\dataset.zst" `
  --selected-servers-path "$Run\manual_selected_servers.parquet" `
  --output-path "$Run\messages.parquet" `
  --exclude-bots `
  --batch-size 50000
if ($LASTEXITCODE -ne 0) { throw "Extraction failed; do not use partial output." }
Get-FileHash "$Run\messages.parquet" -Algorithm SHA256 |
  Export-Csv "$Run\extracted_messages_hash.csv" -NoTypeInformation
```

Current-upstream streaming alternative (run **instead**, not afterwards):

```powershell
uv run --locked python -m discord_data extract-remote `
  --selected-servers-path "$Run\manual_selected_servers.parquet" `
  --output-path "$Run\messages.parquet" `
  --exclude-bots `
  --batch-size 50000
```

Both traverse a zstd tar archive. Members ending in `<guild_id>.json`
are read only for accepted IDs; message rows are JSON lines.
Extraction writes batched zstd Parquet and refuses existing outputs.
It does not physically create one file per server: the output preserves
`guild_id` and `guild_name`, allowing logical separation and later SQL queries.
The historical extracted input contained 31 servers, 689 channels and
13,275,074 records.

Bots are excluded by default. Use `--no-exclude-bots` only for an explicitly
different study. Optional repeated `--include-channel-regex` and
`--exclude-channel-regex` filter channel names case-insensitively; exclusion
wins. Do not add these filters when reproducing the current selection.
Invalid JSON lines are counted and skipped; preserve the console counts.
Failures can leave partial Parquet files: use a new path for the retry and
do not treat file existence as successful completion.

### Extraction schema and provenance limits

The [message schema](../discord_data/extraction.py) preserves server/channel,
message and author IDs; content; bot status; timestamps; message type;
native reply/thread fields; and attachment/embed/mention/sticker/reaction
counts plus serialized payloads. Raw schema names are retained.
Server positive scores are also carried into the extraction.

Extraction does not currently produce its own automatic provenance manifest.
Keep the input archive hash, selected-server artifact and its manifest,
exact command/options, output hash and final extraction counts together.
Later selection manifests hash the extracted Parquet, not the remote archive.

### Optional DuckDB views and server separation

```powershell
uv run --locked python -m discord_data init-duckdb `
  --messages-path "$Run\messages.parquet" `
  --servers-path "$Run\manual_selected_servers.parquet" `
  --database-path "$Run\discord.duckdb"
```

This creates local views, not a second copy of the messages. Keep the
referenced Parquet files at their recorded paths. Query `software_messages` by
`guild_id` to isolate a server. This is corpus organization, not a
train/validation/test split.
