import {useState} from 'react'
import {Button, Checkbox, Dialog, Flash, FormControl, Heading, Select, TextInput} from '@primer/react'
import {AppModel, nativeReply} from './model'
import {native} from './transport'
import {author, time} from './Annotation'
import {explanations, labels} from './labels'

export function ImportForm({model: m}: {model: AppModel}) {
  const [path, setPath] = useState(m.config?.default_source || '')
  async function pick(kind: string) {
    const selected = await native<string | null>('pick_path', {kind})
    if (selected) setPath(selected)
  }
  return <fieldset className="stack" disabled={m.busy}>
    <p>Choose the sampling folder containing sampled_messages.parquet and selected_windows.csv, or annotation_windows.csv. Source files are read-only.</p>
    <FormControl><FormControl.Label>Input folder or file</FormControl.Label><TextInput block value={path} onChange={event => setPath(event.target.value)} placeholder="Select or paste a local path" /></FormControl>
    <div className="actions"><Button onClick={() => void m.run(() => pick('sample_folder'))}>Choose folder</Button><Button onClick={() => void m.run(() => pick('sample_file'))}>Choose CSV / Parquet</Button></div>
    <div className="actions"><Button variant="primary" onClick={() => void m.run(() => m.importSample(path))}>Check and open sample</Button><Button onClick={() => void m.run(() => m.importSample('', true))}>Open demonstration</Button></div>
    <p role="status">{m.importProgress}</p>
    <Flash>The tool preserves supplied targets, context, and native replies. It does not resample or retrieve additional Discord content.</Flash>
  </fieldset>
}

function Identity({model: m}: {model: AppModel}) {
  const [actor, setActor] = useState(m.annotator)
  const [pseudonyms, setPseudonyms] = useState(m.pseudonyms)
  return <fieldset className="stack" disabled={m.busy}>
    <p>Use a stable identifier. Each annotator has an independent set of decisions.</p>
    <FormControl required><FormControl.Label>Annotator identifier</FormControl.Label><TextInput block maxLength={100} value={actor} onChange={event => setActor(event.target.value)} placeholder="e.g., annotator-a" /></FormControl>
    <FormControl><Checkbox checked={pseudonyms} onChange={event => setPseudonyms(event.target.checked)} /><FormControl.Label>Display participants using pseudonyms</FormControl.Label></FormControl>
    <Button variant="primary" onClick={() => void m.run(() => m.saveIdentity(actor, pseudonyms))}>Save identity</Button>
  </fieldset>
}

function Files({model: m}: {model: AppModel}) {
  const config = m.config
  return <div className="stack">
    <p>The workspace contains the database, drafts, history, backups, and exports.</p>
    {config && <><dl className="file-paths"><dt>Active workspace</dt><dd>{config.workspace}</dd><dt>Database</dt><dd>{config.database}</dd><dt>Exported results</dt><dd>{config.exports}</dd></dl>
      <div className="actions"><Button disabled={m.busy} onClick={() => void m.run(() => native('open_local_folder', {path: config.workspace}))}>Open workspace folder</Button><Button disabled={m.busy} onClick={() => void m.run(() => native('open_local_folder', {path: config.exports}))}>Open results</Button><Button disabled={m.busy} onClick={() => void m.run(() => m.backup())}>Create backup</Button></div>
    </>}
    {m.backupPath && <Flash variant="success"><span className="path">Backup created: {m.backupPath}</span></Flash>}
    <Heading as="h3" className="section-title">Use another workspace</Heading>
    <p>Close the previous application, then select its workspace folder containing annotations.sqlite3. An empty folder starts independent work. No database is moved, merged, or replaced.</p>
    <Button disabled={m.busy} onClick={() => void m.run(() => m.switchWorkspace())}>Choose another folder</Button>
    <p className="muted">To restore a backup, close the app and copy it into a new folder as annotations.sqlite3. Never copy only the SQLite file from an open database.</p>
  </div>
}

function Sessions({model: m}: {model: AppModel}) {
  const [label, setLabel] = useState(m.label)
  const [selected, setSelected] = useState(m.state!.session.id)
  return <fieldset className="stack" disabled={m.busy}>
    <p>Resume an existing session, or enter a new label for an independent annotation.</p>
    <FormControl><FormControl.Label>Existing session</FormControl.Label><Select block value={selected} onChange={event => setSelected(event.target.value)}>
      {m.sessions.filter(session => session.annotator_id === m.annotator).map(session => <Select.Option key={session.id} value={session.id}>{session.label} · r{session.graph_revision} · {session.kind === 'adjudication' ? 'Adjudication' : 'Individual'}</Select.Option>)}
    </Select></FormControl>
    <Button onClick={() => void m.run(() => m.openSession(m.state!.session.sample_id, selected))}>Resume session</Button>
    <FormControl><FormControl.Label>Session label</FormControl.Label><TextInput block value={label} onChange={event => setLabel(event.target.value)} /></FormControl>
    <Button variant="primary" onClick={() => void m.run(async () => {
      m.label = label.trim() || 'Primary'
      localStorage.setItem('discord.label', m.label)
      await m.openSession(m.state!.session.sample_id)
    })}>Open or create labeled session</Button>
  </fieldset>
}

function Adjudicate({model: m}: {model: AppModel}) {
  const [actor, setActor] = useState(m.annotator)
  const [label, setLabel] = useState(`Adjudication ${new Date().toLocaleDateString('en-US')}`)
  return <fieldset className="stack" disabled={m.busy}>
    <Flash>Original sessions are preserved. No decisions are copied automatically. Each adjudicated decision requires a rationale; export requires conversation review and interval validation.</Flash>
    <FormControl required><FormControl.Label>Adjudicator identifier</FormControl.Label><TextInput block maxLength={100} value={actor} onChange={event => setActor(event.target.value)} /></FormControl>
    <FormControl required><FormControl.Label>Consolidated session label</FormControl.Label><TextInput block value={label} onChange={event => setLabel(event.target.value)} /></FormControl>
    <Button variant="primary" disabled={!actor.trim() || !label.trim()} onClick={() => void m.run(() => m.adjudicate(actor.trim(), label.trim()))}>Create adjudication session</Button>
  </fieldset>
}

function Guide() {
  return <div className="stack">
    <p>For each target message, decide which earlier messages it replies to. Links point from the reply to its antecedent. Context messages may receive links, but do not require source decisions.</p>
    <ol className="guide-list"><li>Read the source and chronological context. Conversations may be interleaved.</li><li>Inspect native Discord replies. Inspecting and locating do not annotate.</li><li>Select one or more eligible antecedents, or choose a no-link decision.</li><li>Set confidence, uncertainty, and notes. Confirm and advance.</li><li>Review derived conversations, validate the interval, and export.</li></ol>
    {Object.entries(labels).filter(([status]) => status !== 'pending').map(([status, title]) => <section key={status}><Heading as="h3" className="section-title">{title}</Heading><p>{explanations[status as keyof typeof explanations]}</p></section>)}
    <Flash>Draft: resumable editing. Confirmation: saved human decision. Review: graph inspection. Validation: interval acceptance. Boundaries outside the supplied context are never guaranteed.</Flash>
    <Heading as="h3" className="section-title">Keyboard shortcuts</Heading>
    <p>Outside inputs and buttons: Enter confirms; / searches antecedents; Up / Down navigates candidates; L toggles the candidate; N records a new conversation; U records uncertainty; Escape returns to the source; Ctrl / Cmd + Z undoes; Ctrl / Cmd + Shift + Z or Ctrl / Cmd + Y redoes; ? opens this guide.</p>
    <p className="muted">Shortcuts do not override normal input or button activation. Drag pane dividers or focus them and use arrow keys to resize. Use Hide intervals for more space.</p>
  </div>
}

export function Dialogs({model: m}: {model: AppModel}) {
  const close = () => { if (!m.busy) { m.modal = null; m.inspected = null; m.changed() } }
  const inspected = m.inspected
  if (inspected) {
    const reply = nativeReply(m.state?.messages || [], inspected)
    return <Dialog title={`Message #${inspected.sequence}: metadata and reply evidence`} width="xlarge" onClose={close}>
      <div className="stack">
        <p>{author(inspected, m.pseudonyms)} · {time(inspected.timestamp)}</p><p className="message-text">{inspected.content || '[Message has no text]'}</p>
        {reply.id && <><Heading as="h3" className="section-title">Replies on Discord to</Heading>
          {reply.target ? <><p>#{reply.target.sequence} · {author(reply.target, m.pseudonyms)}</p><p className="message-text">{reply.target.content || '[Message has no text]'}</p>
            <Button disabled={m.busy} onClick={() => void m.run(async () => { m.reveal(reply.target!.message_id); await m.changeTab('annotate'); m.inspected = null })}>Locate referenced message in stream</Button>
          </> : <Flash>Reference {reply.id} is outside this interval. No content is retrieved and no invisible human link can be created.</Flash>}
          <Button variant="primary" disabled={m.busy || inspected.message_id !== m.work || !reply.eligible || m.draft?.edges.some(edge => edge.target_message_id === reply.id)} onClick={() => { try { m.addNative(inspected); m.changed() } catch (error) { m.report(error) } }}>Add as antecedent to my draft</Button>
          <p className="muted">Adding does not confirm the decision.</p>
        </>}
        <details><summary>Inspect imported metadata</summary><pre>{JSON.stringify(inspected, null, 2)}</pre></details>
      </div>
    </Dialog>
  }
  if (!m.modal) return null
  const titles = {
    identity: 'Local annotator identity', import: 'Open a local sample', files: 'My files',
    guide: 'Annotation guide', sessions: 'Sessions for this interval', history: 'Session history',
    provenance: 'Sample provenance', export: 'Export current session', adjudicate: 'New adjudication session',
    close: 'The application is still open',
  }
  const currentImport = m.imports.find(item => item.id === m.importId)
  return <Dialog title={titles[m.modal]} width="xlarge" onClose={close}>
    <div className="stack">
      {m.error && <Flash variant="danger" role="alert">{m.error}</Flash>}
      {m.busy && <p role="status">{m.importProgress || 'Working locally...'}</p>}
      {m.modal === 'identity' && <Identity model={m} />}
      {m.modal === 'import' && <ImportForm model={m} />}
      {m.modal === 'files' && <Files model={m} />}
      {m.modal === 'guide' && <Guide />}
      {m.modal === 'sessions' && <Sessions model={m} />}
      {m.modal === 'adjudicate' && <Adjudicate model={m} />}
      {m.modal === 'provenance' && <><p className="path">{currentImport?.source_path}</p><pre>{JSON.stringify(currentImport?.provenance, null, 2)}</pre></>}
      {m.modal === 'history' && <><p>Up to 300 recent events, including undo and redo.</p>{m.history.map(event => <article key={event.id} className="panel"><strong>{event.event_type}</strong><p className="muted">r{event.revision} · {time(event.created_at)} · {event.actor_id} · {event.source_id}</p>{event.after_data && <details><summary>Inspect change</summary><pre>{JSON.stringify(JSON.parse(event.after_data), null, 2)}</pre></details>}</article>)}</>}
      {m.modal === 'export' && m.state && <>
        <p>Annotator: <strong>{m.state.session.annotator_id}</strong> · Interval: {m.state.session.sample_id} · Revision: {m.state.session.graph_revision}</p>
        <Flash variant={m.state.validated && !Object.keys(m.state.drafts).length && !m.dirty ? 'success' : 'warning'}>{m.state.validated && !Object.keys(m.state.drafts).length && !m.dirty ? 'Validated interval.' : 'Work in progress; this status is preserved in the export.'} Drafts are excluded from human labels.</Flash>
        <p>Creates CSV / JSON summaries, human and derived Parquet data, compatible inputs, reviews, a manifest with provenance, and a pipeline-compatible data ZIP. Counts are descriptive, not corpus prevalence estimates.</p>
        <Button variant="primary" disabled={m.busy} onClick={() => void m.run(() => m.export())}>Generate local results</Button>
        {m.lastExport && <><p className="path">{m.lastExport.directory}</p><Button disabled={m.busy} onClick={() => void m.run(() => native('open_local_folder', {path: m.lastExport!.directory}))}>Open results folder</Button><details><summary>Export manifest</summary><pre>{JSON.stringify(m.lastExport.manifest, null, 2)}</pre></details></>}
      </>}
      {m.modal === 'close' && <>
        <p>The draft could not be saved or the processor could not shut down. Saved decisions are preserved. Continue working or try again.</p>
        <div className="actions"><Button onClick={close}>Continue working</Button><Button variant="primary" onClick={() => void m.close()}>Retry saving and closing</Button></div>
        {(m.dirty || m.saveError) && <><Flash variant="warning">Closing without saving loses changes not yet written to the database.</Flash><Button variant="danger" onClick={() => void native('finish_close', {force: true}).catch(error => m.report(error))}>Close without saving these changes</Button></>}
      </>}
    </div>
  </Dialog>
}
