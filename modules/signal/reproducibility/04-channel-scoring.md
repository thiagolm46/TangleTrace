# 4. Optional Profile-Based Channel Scoring

[Previous: current selection](03-channel-selection.md) | [Next: validation](05-validation-and-preparation.md)

This diagnostic scorer is separate from the current participant-based
selection. **Do not describe A-D scores as the origin of the 297-channel
corpus.** The server-only v2 profile cannot score channels.

## Reproducible Command

Use the channel-capable
[software.engineering.v1.json](../configs/filtering/software.engineering.v1.json)
(profile version `1.1.0`):

```powershell
$ChannelProfile = "configs\filtering\software.engineering.v1.json"
uv run --locked python -m discord_filtering validate-profile --profile $ChannelProfile
uv run --locked python -m discord_filtering score-channels `
  --profile $ChannelProfile `
  --input "$Run\messages.parquet" `
  --guild-id 787399249741479977 `
  --min-messages 50 `
  --output "$Run\neo4j_channel_scores.parquet"
```

Choose exactly one scope: `--guild-id`, `--guild-name` (exact match), or
`--all-guilds`. The Neo4j ID is an example of a server in the historical
accepted set. All-guild scoring can require substantial memory.

Input must be Parquet containing `channel_id`, `channel_name` and `content`,
plus the selected guild filter column. Author, bot, timestamp, message ID,
reply and mention fields are used when present. Optional channel metadata
fields are `channel_category`, `channel_description` and `topic`; the current
extractor does not populate them. Missing metadata is not fabricated.

The older [software.v1.json](../configs/filtering/software.v1.json) is another
supported profile with different rules and weights. Do not interchange
profiles or compare their scores as if they were the same scale.

## Score Components for Engineering v1

1. **Metadata:** score positive and negative rules across configured channel
   metadata with `max_per_group`, then
   `M = min(max(P_metadata - N_metadata, 0) / 4, 1)`.
2. **Content:** for each signal, count messages containing a regex match,
   not the number of repeated occurrences in a message.
   The bounded signal ratio is
   `min((matching_messages / n_messages) / saturation_ratio, 1)`;
   it is zero when there are no counted messages.
3. **Lexical and domain evidence:** sum bounded signal ratios times their
   respective weights and cap each component at 1.
   This profile has one technical signal with saturation ratio **0.1**
   and weight **1** in both components, so `L = D`.
4. **Combined score:** `S = 0.2*M + 0.6*L + 0.2*D`, capped at 1.
   Emitted component/combined scores are rounded to six decimal places.

Bots are excluded from content counts by this profile. `n_messages` is the
number of counted non-excluded messages, not usable-payload volume.
Messages without text still contribute to its denominator.
Signal examples are bounded to five per signal and link matches to message
IDs. They can contain source excerpts: protect scores and evidence under
the same access policy as the source.

## Ordered A-D Classification

The first matching branch wins:

| Order | Condition | Class |
| --- | --- | --- |
| 1 | Administrative metadata label, `L < 0.3` and `D < 0.2` | D |
| 2 | Social metadata label and `L < 0.35` | C |
| 3 | `S >= 0.7` and `L >= 0.3` | A |
| 4 | `S >= 0.5` OR (`L >= 0.45` and `D >= 0.2`) | B |
| 5 | Remaining administrative metadata label | D |
| 6 | Otherwise | C |

A is the high-confidence class; B requires review; C/D represent
social/administrative classifications. Labels are heuristic, not validated
human truth.

## Conversation Suitability and Eligibility

An A class alone does **not** imply `include_in_main_analysis=true`.
This profile also requires all suitability conditions:

- At least 5 observed counted authors.
- Interaction ratio at least 0.05.
- Author transition ratio at least 0.2.
- Dominant-author share at most 0.7.
- Bot share at most 0.25.

Interaction is a reply referencing an earlier counted message ID in the
same channel, or a positive mention count. Messages are sorted by timestamp
string then message ID. This is an observable proxy, not inferred semantic
reply correctness or a requirement that every message has a reply.
Author transitions use successive identified authors; dominance divides
the largest author's count by all identified-author messages.
The scorer falls back to author username if author ID is absent, and its
bot parsing is not the strict SQL `is_bot = false` definition of the current
participant selector. These metrics must not substitute for that selector's
distinct-human-author count.

The reported `conversation_score` averages saturated user, interaction,
transition and inverse-dominance components plus `1 - bot_share`.
The boolean `conversation_suitable` checks each threshold individually,
not a cutoff on that average.

Final inclusion requires an allowed class (A in this profile), conversation
suitability and the CLI minimum `n_messages >= --min-messages` (default 50).
Low-volume channels remain in the output with their scores/classes, but
receive `eligibility_status=insufficient_data`,
`include_in_main_analysis=false` and `manual_review_required=true`.
B channels and unsuitable A channels also require review.

The output preserves identity, component scores, class, counts, conversation
diagnostics, inclusion/review flags and evidence. An adjacent manifest hashes
the profile, source and output and records scope/minimum/counts.
No messages are automatically removed by `score-channels`: it writes a
channel decision table. If using this alternative for a new study, freeze an
explicit review and selection policy before materializing any corpus.
