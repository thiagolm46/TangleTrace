tabela e `messages.parquet`.
a outro.
# Conversational Annotation Codebook

**Version:** 1.1  
**Annotation unit:** a continuous window from a Discord channel

## 1. Data Structure

`native_reply_annotation_windows.csv` is the preparation artifact. Before annotation, flatten it with `build-annotation-bundle` into three Parquet tables. The canonical annotation tables are `messages.parquet` and `annotations.parquet`.

### `messages.parquet`

Each row is a canonical server message. `message_id` is unique, and `content` appears once alongside its native metadata.

```text
message_id, server_id, channel_id, author_id, timestamp, content,
native_reply_to, mentions, message_type, reaction_count, has_attachment, is_bot
```

The file also includes preserved native metadata such as reactions, attachments, embeds, threads, webhooks, flags, and the source payload.

### `sample_messages.parquet`

Each row records a message's participation in an annotation window:

```text
sample_id, message_id, is_context, sequence
```

A message may appear in multiple samples because context from one window can overlap the annotated segment of the next. The key is `(sample_id, message_id)`. `is_context=true` indicates preceding context; `is_context=false` indicates a target segment. To obtain a complete sample, join this table to `messages.parquet` on `message_id`.

### `annotations.parquet`

Each row is a directed human edge. The same `source_message_id` may appear in multiple rows within one `sample_id`.

```text
sample_id, source_message_id, target_message_id, annotator_id, relation,
ambiguous, confidence, notes
```

In the initial codebook, `relation=reply` is the only materialized relation. Ambiguous edges are preserved but excluded from derived gold by default; use `--include-ambiguous` to include them explicitly.

### `source_statuses.parquet`

This third table is required for human decisions without an edge. Each target-segment source has one row with `source_status`; therefore, the absence of a row in `annotations.parquet` never means `no_reply`.

Only participations with `is_context=false` require a decision. Every visible earlier message, including one with `is_context=true`, is an eligible antecedent.

## 2. Native Discord Evidence

`native_reply_to_message_id` preserves the platform's explicit reference.

| Condition | Required interpretation |
|---|---|
| `native_reply_to_message_id != null` | Positive observed evidence of a native edge `(source, target)` |
| `native_reply_to_message_id == null` | No native relation was observed; this is not negative evidence, `no_reply`, or a conversation start |

In particular, the absence of a native reply must never create a negative pair, exclude a semantic parent, or split a conversation. For this reason, `native_reply_evidence` uses only `positive_observed` and `unknown`.

Edges in `native_reply_edges_json` are partial silver evidence. They do not constrain human annotations: a message without a native reply may receive an annotated semantic parent.

For example, if only `M5` explicitly quotes `M1`, annotation may record `M2 -> M1`, `M3 -> M1`, `M4 -> M1`, and `M5 -> M1` when the content supports those relations.

## 3. Metadata Preservation

The silver artifact preserves identifiers, channel/server, author, original and edited timestamps, content, message type, native replies, mentions, reactions, attachments, embeds, stickers, mentioned roles, flags, bot/webhook status, pin state, and native thread. `native_fields_json` retains additional source fields. `native_available_fields` identifies which fields were present in the source for each message: a field missing from the source must not be interpreted as an empty list, false value, or negative evidence.

These fields are annotation evidence and material for later study. No field automatically becomes a feature, gold label, or negative label.

## 4. Primary Human Edges

Annotators do not assign `conversation_id` or fill a single-parent field. The primary unit is a row in `annotations.parquet`. A source may appear in one or more edges:

```json
[
  {
    "source_message_id": "M20",
    "target_message_id": "M17",
    "target_location": "context"
  },
  {
    "source_message_id": "M20",
    "target_message_id": "M18",
    "target_location": "annotated"
  }
]
```

Each edge asserts that the source semantically replies to the target. The source must be in the `annotated` segment; the target must be visible, strictly earlier, and part of the same `sample_id`. The target may be in the context or annotated segment; its position is determined by `is_context` in `messages.parquet`.

`source_statuses.parquet` contains one decision for each target-segment source, but it does not encode a parent-child relation. Allowed `source_status` values:

- `pending`: annotation is still open;
- `complete`: the source's list of zero or more edges is finalized;
- `no_reply`: after review, no semantic reply relation was assigned;
- `outside_context`: there is evidence of an antecedent before the visible context;
- `ambiguous`: the evidence does not support a decision;
- `new_conversation`: the annotator explicitly judged that a clear new topic starts here.

The materializer accepts edges only from sources with status `complete`. `no_reply`, `outside_context`, and `ambiguous` create no edges and do not imply that a new conversation starts. `new_conversation` is the only decision that creates a singleton conversation: during materialization only, it becomes the compatible self-link `M30 -> M30`. A parent outside the window is never invented.

## 5. Conversation Grouping

After completing the edges, run:

```powershell
discord-disentangle derive-annotation-components `
  --messages <messages.parquet> `
  --sample-messages <sample_messages.parquet> `
  --annotations <annotations.parquet> `
  --source-statuses <source_statuses.parquet> `
  --output <human_gold_directory>
```

The command validates edges and writes `human_reply_edges.parquet` and `human_reply_components.parquet`. The second file computes `conversation_id` as the undirected connected component of human edges. Given edges `M10 -> M4`, `M11 -> M4`, `M12 -> M7`, `M13 -> M10`, and `M13 -> M11`, messages `M4`, `M10`, `M11`, and `M13` belong to one component; `M7` and `M12` belong to another.

Thus, `conversation_id` is derived and reproducible, not an annotator-assigned label. Only messages participating in at least one human edge receive a component; sources without edges are not automatically converted to singleton conversations.

## 6. Initial Decision Rules

| Case | Decision |
|---|---|
| Explicit native reply | Strong positive evidence; review and record the human edge when semantically compatible. |
| `@mention` | Evidence of a recipient, not an automatic antecedent. |
| Reply without a mention or native reply | Allow a semantic edge when supported by content and context. |
| Multiple replies to one message | They may all point to the same antecedent. |
| Message replying to several earlier messages | Record one `reply` row per antecedent. |
| Clear topic start | Set `source_status=new_conversation`; do not create a self-link manually. |
| Continuation by the same author | Examine content and context; shared authorship is not an automatic link. |
| “yes,” “no,” “thanks” | Look for an antecedent in context; do not assume the immediately preceding message. |
| Antecedent before the target segment | Search the context; if still invisible, use `outside_context`. |
| No identifiable antecedent | Use `no_reply`; do not force a link. |
| Uncertain message or relation | Set `ambiguous=true` on an edge, or use `source_status=ambiguous` when no edge is defensible. |

## 7. Pilot and Review

Before large-scale annotation, run three pilot rounds. After each round, compare disagreements, record consensus decisions, and add anonymized difficult-case examples to the codebook. Priority cases include repeated questions, multiple antecedents, interjections, short replies, replies without mentions, and topic boundaries.

## 8. Review and Privacy

Record annotator identity, date, ambiguity, and notes in the window record. Raw content and message payloads remain in local artifacts ignored by Git; do not copy them into spreadsheets or version-controlled documents.