# 5. Validation and Optional Downstream Preparation

[Guide index](README.md) | [Previous: scoring](04-channel-scoring.md)

## Validation Checklist

1. Record the repository commit, dirty state, Python/uv versions and locked
   dependency environment.
2. Freeze metadata and archive revisions and SHA-256 hashes.
3. Validate profiles; distinguish server-only scoring from channel-capable
   profiles.
4. Inspect the score manifest and candidate quartiles/counts.
5. Apply an explicit review covering every candidate exactly once.
6. Require successful extraction; retain options, final counts and hashes.
7. Run channel selection in a new directory and require `verify` to pass.
8. Reconcile retained counts with the reference only when inputs match.
9. Keep original manifests immutable. New timestamps/paths and translated
   profile-description hashes need not equal historical manifests.

```powershell
uv run --locked python -m pytest tests -q
uv run --locked python -m discord_filtering.channel_selection verify "$Run\participants"
```

The suite covers profile validation, score evidence, server review,
extraction, resumed downloads, participant boundaries, selection integrity,
population accounting, sampling and preparation. Tests use synthetic/local
fixtures and do not download the full dataset.

## Optional Population Characterization

Continue using the **new** retained corpus, not implicit historical defaults:

```powershell
uv run --locked python -m discord_disentanglement population `
  --input "$Run\participants\messages.parquet" `
  --output "$Run\population"
uv run --locked python -m discord_disentanglement population-report `
  --input-dir "$Run\population" `
  --output "$Run\population.md"
```

Payload usability is separate from channel eligibility. Only simultaneous
absence of nonblank text and recorded attachment/embed/sticker is unusable.
Missing IDs, invalid timestamps and duplicate keys are separate structural
flags. A usable human message has content and explicit non-bot status.
Native reply summaries are observed platform evidence, not semantic labels.

Generated reports are English, with comma thousands separators and decimal
points. Their default paths are under the processed data tree, not
the preserved research documentation.

## Optional Frame, Sample and Audit

```powershell
uv run --locked python -m discord_disentanglement prepare-frame `
  --channels "$Run\population\channels.csv" `
  --output "$Run\channel_frame.csv"
```

Review the resulting eligibility register before a definitive study. Its
automatic states are provisional, not human conversation annotations.
Keep a frozen copy of any reviewed frame and explain changes.

```powershell
uv run --locked python -m discord_disentanglement draw `
  --input "$Run\participants\messages.parquet" `
  --frame "$Run\channel_frame.csv" `
  --output "$Run\sample" `
  --seed 20261014 `
  --channels-per-stratum 2 `
  --periods-per-channel 3 `
  --windows-per-period 1 `
  --target-messages 100 `
  --context-messages 200
uv run --locked python -m discord_disentanglement audit-sampling `
  --sample "$Run\sample" `
  --output "$Run\sampling_audit" `
  --report "$Run\sampling_audit.md"
```

Sampling is hierarchical by server x channel-size stratum, active UTC month
and target block. Size defaults are small up to 1,000 usable human messages,
medium up to 10,000, and large above that. Final incomplete blocks remain in
the frame. Preserve each level's inclusion probability, their product,
inverse-probability weights and the seed.

For the historical frame and corpus, the reference draw had 107 channels,
317 windows and 17,921 target messages. Changed eligibility or sources can
change these results. The audit checks the frozen draw; it does not silently
filter or redraw it. Correct probabilities do not certify semantic usefulness.

## Handoff to TangleTrace BETWEEN

TangleTrace SIGNAL (`tangletrace-signal`) writes the sample directory in the
preceding step. BETWEEN (`tangletrace-between`) is a separate local annotation
application. It can import that directory, containing `sampled_messages.parquet`
and `selected_windows.csv`, or the `annotation_windows.csv` file. The
canonical bundle below is a separate output and is not BETWEEN's direct
import format.

## Optional Annotation Tables

```powershell
uv run --locked python -m discord_disentanglement build-annotation-bundle `
  --annotation-windows "$Run\sample\annotation_windows.csv" `
  --output "$Run\annotation_bundle"
```

The bundle separates canonical messages, target/context membership, human
edge tables and source states. Native replies are silver evidence; missing
replies are never negative semantic labels. This produces annotation inputs,
not trained models or a completed benchmark.

`publish-annotation-dataset` additionally requires explicit
`--bundle-dir`, `--native-reply-edges`, `--codebook` and `--output`.
It does not infer the native-edge file. Use an approved codebook and follow
the access policy before publishing source content.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Output already exists | Choose a new run/output path; do not erase historical runs |
| Candidate/review IDs differ | Check snapshot/profile; conduct a new review if this is a new corpus |
| No positive affinity scores | Check metadata schema and profile; Tukey prioritization requires positive evidence |
| Unmatched exclusion name | Check source and exact Unicode/case; use an explicitly revised list for a new study |
| Channel profile missing | Use a channel-capable v1 profile, not server-only v2 |
| Channel scoring exhausts memory | Score one guild at a time; it loads that scope into pandas |
| Remote resume rejected | Preserve the failure; retry to a new path or download a frozen local archive |
| Selection hash mismatch | Treat outputs as changed/corrupt; rerun from frozen inputs into a new directory |
| Reference counts differ | Compare source hashes, review, exclusions, bot options and thresholds before interpreting results |
| Partial extraction after failure | Do not consume it; retain logs and rerun to a fresh destination |

Use `uv run --locked python -m <module> <command> --help` for complete CLI
options. No operation in this manual requires editing or regenerating the
existing files under [docs](../docs).
