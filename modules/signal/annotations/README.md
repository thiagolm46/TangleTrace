# Participant Frame and Provenance

The current [channel frame](channel_frame_participants_v2.csv) was generated
after selecting channels with at least 500 exported records and five distinct
human authors. It contains 297 channels from 29 servers with provisional
eligibility states, not annotated conversation labels.

The source, recalculated statistics, channel decisions and hashes are in
`data\processed\filtering\software\participants_v2`. Verify with:

```powershell
uv run --locked python -m discord_filtering.channel_selection verify
```

The [historical package](channel_selection_2026-10-07) and earlier register
are archives, preserved without replacement. They are not inputs to the
current selection, frame or sample. The active workflow does not use
reply- or mention-conditioned author counts.

For English reproduction instructions, see
[channel selection](../reproducibility/03-channel-selection.md) and
[downstream preparation](../reproducibility/05-validation-and-preparation.md).
The original [annotation codebook](../docs/methodology/ANNOTATION_CODEBOOK.md)
remains unchanged.
