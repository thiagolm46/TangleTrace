# Reproducing TangleTrace SIGNAL

SIGNAL (`tangletrace-signal`) prepares and samples Discord corpora for
TangleTrace, an auditable workbench for conversation annotation.
**TangleTrace BETWEEN** (`tangletrace-between`) is the separate reply-link
annotation and review application; it is not part of this repository.

This is the English operational manual. It is independent of the preserved
research notes in [docs](../docs). Run every command from the repository root
in **PowerShell**. Steps share the variables established in the setup page.

## Reading and Execution Order

1. [Environment, source snapshots and run layout](01-setup-and-sources.md)
2. [Server scoring, review and extraction](02-server-filtering.md)
3. [Current channel selection and verification](03-channel-selection.md)
4. [Optional profile-based channel scoring](04-channel-scoring.md)
5. [Validation and optional downstream preparation](05-validation-and-preparation.md)

The main reproduction path is **1 -> 2 -> 3 -> verification in 5**.
Step 4 is an alternative diagnostic path, not an additional hidden gate in
Step 3. Population characterization and annotation preparation are optional.

```text
Frozen server metadata + server scoring profile
  -> all-server scores + evidence
  -> positive-score Tukey candidate queue
  -> recorded human accept/reject decisions
  -> accepted server IDs
Frozen Discord Unveiled archive + accepted IDs
  -> extracted message Parquet
  -> exact-name exclusions AND minimum volume AND minimum human authors
  -> retained corpus + statistics + decisions + manifests

Optional: extracted messages + channel-capable profile -> channel scores A-D
Optional: retained corpus -> population -> reviewed frame -> sample
Optional: sample -> BETWEEN (direct import) OR canonical annotation tables
```

## What "Reproducible" Means Here

- **Computational:** the same source records, profile rules and parameters
  reproduce the scores and operational decisions.
- **Decision replay:** the checked-in accept/reject table and exact exclusion
  names reproduce recorded human decisions. They do not prove independent
  reviewer agreement. Per-server and per-channel rationales were not preserved.
- **Provenance:** preserve source hashes, revision identifiers, commands,
  configuration files, manifests and the repository commit for every run.
- **Not byte identity:** paths, timestamps, implementation hashes, Parquet
  serialization and execution order can differ between machines. Compare
  keyed records, scores and counts as well as file integrity.

The reference source metadata contained 3,167 servers. The reconstructed
queue contained 37 candidates, of which 31 were accepted. The current channel
run retained 297 channels from 29 servers and 11,897,859 exported records.
These are historical reference results, not promises about upstream `main`.

## Language and Compatibility

CLI help, errors, generated report prose and this manual use English.
Identifiers, message content, exact channel names and multilingual regex
alternatives remain unchanged. Those strings are data or matching semantics,
not untranslated interface text.

Only profile descriptions were translated; rule weights, expressions,
thresholds, IDs and profile versions were not changed. Consequently **profile
file hashes differ from historical manifests even though scores do not**.
Never edit an old manifest to make it match the translated file. Keep the
original profile snapshot when checking historical byte hashes; use newly
generated manifests for new runs.

The new commands `prioritize-servers` and `apply-server-review` replace
previously implicit/manual materialization steps. Existing module names and
commands remain available. Channel selection now defaults to the versioned
English-named exclusion file rather than a local, untracked legacy filename.
Generated population and sampling reports default to the data output tree,
so reproductions do not overwrite the preserved research documentation.
