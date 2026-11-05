# Functional and Technical Specification: TangleTrace BETWEEN

**Version:** 0.3 desktop implementation  
**Scientific contract:** Codebook 1.1  
**Audience:** artifact evaluators, researchers, and maintainers

> This English, implementation-focused specification supersedes the unreconciled 0.2 proposal for the artifact release. It describes behavior present in the current code. The scientific annotation rules are defined in [CODEBOOK_v1.1.md](CODEBOOK_v1.1.md); reproducible setup and verification are defined in [REPRODUCIBILITY.md](REPRODUCIBILITY.md).

## 1. Purpose and Scope

BETWEEN supports human annotation of **reply-to-antecedent relations** in already sampled Discord message windows. Samples can be prepared by TangleTrace SIGNAL (`tangletrace-signal`) or another compatible source. Annotators select zero or more earlier messages that a target replies to. Conversation components are derived from confirmed human links; annotators do not assign conversation IDs directly.

The application is a local research tool. It does not sample the corpus, retrieve new Discord data, classify toxicity, call AI services, or estimate population prevalence. A window is an observed package, not a guarantee of complete conversation boundaries.

## 2. Supported Artifact

The supported release is a Windows x64 desktop application built with Tauri 2 and Rust, with a Python worker for data processing and persistence. The interface is bundled with the desktop host. The worker communicates with Rust through a line-oriented JSON protocol over stdin/stdout. The desktop path does not start an HTTP server.

Development and packaging prerequisites, commands, automated checks, and known environment limits are maintained in the README and reproducibility protocol rather than duplicated here.

## 3. Input Data

The importer accepts either:

- A sampling directory containing `sampled_messages.parquet` and `selected_windows.csv`.
- An `annotation_windows.csv` file containing serialized window data.

A source manifest and hashes are checked when present. Missing manifests are recorded as provenance diagnostics; mismatched hashes stop the import. Importing does not resample, filter, or modify source files. A synthetic demonstration is available and does not require research data.

Window and message identifiers, source order, target/context roles, channel/server identity, timestamps, and native reply references are preserved or validated according to the reader contract. Context messages may be antecedents but do not require source decisions.

## 4. Annotation Contract

An edge points from a reply/source message to an antecedent/target message. A target may have zero or multiple antecedents. An eligible antecedent must be visible in the same window, channel, and server and must occur strictly before the source. Human decisions and native platform replies remain separate.

The supported `source_status` values are:

| Value | Meaning |
| --- | --- |
| `pending` | No decision has been confirmed yet. |
| `complete` | The reviewed list of zero or more human antecedents is final. |
| `no_reply` | No semantic reply relation was assigned after review. |
| `outside_context` | Evidence suggests an antecedent before the visible context. |
| `ambiguous` | Available evidence does not support a decision. |
| `new_conversation` | The annotator explicitly judged that a new topic begins. |

Only non-ambiguous edges from `complete` sources connect components by default. `new_conversation` may materialize as a singleton using the compatibility behavior of the existing materializer. Other no-link states do not imply a singleton or a negative training example. See the codebook for decision examples and edge cases.

## 5. Native Evidence

`native_reply_to_message_id` records an explicit Discord reply reference. The interface allows annotators to inspect the reference, locate it in the stream, and explicitly add it to a draft. Inspection and navigation do not modify decisions; adding a reference does not confirm it.

A missing native reply is unknown evidence, not proof that no semantic reply exists. An external or invalid reference is displayed without inventing message content or a visible human edge.

## 6. Annotation Workflow

1. Set a stable annotator identifier and import a sampled input.
2. Choose a window and read its chronological stream and context.
3. For each target, select one or more eligible antecedents or choose a no-link status.
4. Review the draft, confidence, and notes, then explicitly confirm the decision.
5. Inspect derived conversation components and mark them reviewed.
6. Complete the global interval checklist before validating the interval.
7. Export a session snapshot with its manifest and provenance.

Drafts autosave for recovery but do not enter confirmed labels. A validated individual session remains an individual annotation; validation alone does not produce adjudicated gold.

## 7. Sessions, Review, and Adjudication

Sessions are isolated by annotator and label. Confirmations use optimistic graph revisions and transactional persistence. Conversation reviews are attached to a signature of the reviewed component and are invalidated when the relevant graph changes. Interval validation is tied to a graph revision and is invalidated by subsequent changes.

Comparison is explicit and uses eligible sets for decision agreement, link overlap, and grouped-pair overlap. Pending, unresolved, and ambiguous cases are not implicit negatives. Adjudication creates a third session, retains references to its base sessions and revisions, copies no decisions automatically, and requires a rationale for each resolved source. Adjudicated export requires completed, unchanged base sessions and global validation.

## 8. Persistence and Audit

The local SQLite database stores imports, windows, sessions, confirmed decisions, drafts, review records, and event history. The schema remains compatible with the earlier 0.2 database. Backups are created before export; exports receive new directories and do not overwrite earlier results.

A workspace lock prevents simultaneous desktop workers from writing to the same database. The native host restricts commands to an allowlist; the frontend cannot issue shell commands. Desktop users can select a workspace explicitly.

## 9. Exported Artifact

Each export represents one session and one window. It contains a manifest with version, revision, status, provenance, source hashes when available, and output hashes. It also includes descriptive `summary.csv` and `summary.json` files, human annotation tables, derived graph tables, input-compatibility data, and review/history records.

Drafts are excluded from labels. Counts describe the imported sample and confirmed session snapshot; they are not population estimates. Native reply evidence and human-confirmed links remain distinguishable. The export executes the existing materializer and checks its components against the interface derivation.

## 10. Architecture and Data Boundaries

Rust/Tauri owns the desktop window, native file dialogs, workspace selection, and worker lifecycle. The Python worker owns importing, domain validation, SQLite operations, session workflows, and export. Static JavaScript/CSS render the interface and call the host through the internal JSON protocol.

The application reads source sampling artifacts and writes its local workspace and export directories. It does not modify source data. Research content is not included in the application distribution.

## 11. Privacy and Scientific Limitations

Raw message text and exported payloads may contain sensitive research data. Keep workspaces and exports local and follow the study's data-sharing restrictions. Pseudonyms in the interface do not anonymize exported message content.

Components represent only observed, confirmed relations within the sampled window. The application does not recover missing history, establish true conversation boundaries, or infer toxicity or population-level prevalence. Sampling weights remain available for downstream analysis; this tool does not recompute the sampling design.

## 12. Verification

The automated verification commands and expected scope are listed in [REPRODUCIBILITY.md](REPRODUCIBILITY.md). The interface and desktop smoke tests use synthetic data. They do not replace visual inspection of native dialogs, scaling, keyboard accessibility, or operation on a separate clean Windows machine. See [DESKTOP_VALIDATION.md](DESKTOP_VALIDATION.md) for the recorded verification results and remaining limitations.
