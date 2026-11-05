# User Guide · TangleTrace BETWEEN

BETWEEN supports reply-link annotation and review of windows prepared by TangleTrace SIGNAL (`tangletrace-signal`) or another compatible source.

## Open and Locate Your Work

For a newly built distribution, open `tangletrace-between.exe` and keep the `worker` folder beside it. Older distributions use `discord-se-desktop.exe`. From the source directory, run `start-desktop.cmd`. The window is resizable; at narrower widths, panes stack vertically. On desktop, the message stream and editor have independent scrolling and use the available height.

**My files** shows the active workspace, database, and results. To resume an earlier installation, close it and select its `workspace` folder containing `annotations.sqlite3`. Choosing an empty folder starts an independent workspace. Existing files are not replaced.

## Prepare to Annotate

1. Enter your annotator identifier. Reuse it for future sessions.
2. Select the sampling folder or an input CSV/Parquet file.
3. Click **Check and open sample** and follow the progress indicator.
4. Choose an interval on the left. Counts distinguish targets from context.

To explore the workflow without using research data, open the synthetic demonstration.

## Understand the Panes

- **Left — Choose interval:** sampled windows, search, counts, and per-annotator progress.
- **Center — Read messages:** chronological stream. Conversations may still be interleaved. Targets and context are identified.
- **Right — Annotate source:** the message receiving your decision, reply evidence, selected antecedents, status, confidence, and notes.

Use **Hide intervals** to free space. Drag a Primer pane divider, or focus it and use the arrow keys to resize. Widths are remembered locally. **Target X of Y** counts only messages requiring annotation; `#` is the stream position, including context. The interface follows your system light/dark preference.

## Record a Decision

Read the source and context. Use **Select antecedent** on one or more earlier messages, or search for antecedents in the editor. Use **Remove antecedent** to undo selection. To hide selection actions while reading, use **Explore without selecting**. Merely clicking message text never creates a link.

Blue boxes show Discord replies. **Inspect reply** displays both texts; **Locate in stream** jumps to the reference; **Add as antecedent** adds the relation to the draft. You remain responsible for judging and confirming it.

If no antecedent should be recorded, choose a no-link decision. The explanation below the selector describes each option; **Annotation guide** opens the full guide. Remove existing links before choosing a no-link decision. Set confidence and notes, then click **Confirm decision and advance**.

Drafts are saved after a brief pause and before navigation. Closing requests a final save but does not confirm the decision. Reopen the same session to resume a draft. Discarding it restores the last confirmed decision.

## Review and Export

In **2. Conversations**, inspect each component, correct sources if needed, and mark the conversation reviewed. In **3. Validate interval**, inspect pending and uncertain cases, complete the checklist, and validate.

Click **Export**, check the annotator, interval, and revision, then generate results. **Open results folder** opens File Explorer. `summary.csv` contains numeric metrics; `summary.json` also identifies the session. `human/` and `derived/` contain Parquet files. The manifest marks exports as in progress or validated.

Exports are created per session and interval. They do not automatically combine annotators or turn an individual session into gold. Use comparison and adjudication to consolidate decisions.

## Compare and Adjudicate

Use **Sessions** to resume a labeled session or create a separate annotation. In **Compare sessions**, select two sessions for the same interval and click **Compare**. Agreement metrics exclude unresolved cases. **Create adjudication** is available for independent sessions from different annotators; it creates an empty consolidated session without replacing either source. Each adjudicated decision requires a rationale. Adjudicated export requires full review and validation.

## Keyboard Access and Language

Tab navigates Primer controls; Enter/Space activate the focused button. Outside inputs and buttons, Enter confirms the current decision, `/` focuses antecedent search, Up/Down choose a candidate, and `L` toggles it. `N` records a new conversation and `U` records uncertainty when no links are selected. Escape returns to the source; Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z undo/redo; `?` opens the guide. Shortcuts do not override normal text editing or button activation.

Application text is English. Imported messages, identifiers, paths, and saved annotation notes are not translated or modified.

## Recovery and Troubleshooting

**I cannot see my work:** check the active workspace, annotator, and session label. Browser and desktop preferences are separate; the database can be reused.

**Another instance is using the folder:** close the other window. Do not delete database files or the lock to force access.

**Saving failed:** keep the window open and check folder permissions and available disk space. Choose to close without saving only if you accept losing changes not yet written.

**Backup:** choose My files → Create backup. To restore, close the application, copy the backup into a new folder as `annotations.sqlite3`, and select that folder. Do not copy only the SQLite file from an open database; data may still be in the WAL.

**Missing later context:** the interface shows the imported package. It does not retrieve new Discord messages or complete conversation boundaries.
