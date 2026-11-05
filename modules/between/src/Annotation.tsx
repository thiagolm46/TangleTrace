import {useEffect, useRef, useState} from 'react'
import {Button, Checkbox, Flash, FormControl, Heading, Label, PageLayout, Select, Textarea, TextInput} from '@primer/react'
import {AppModel, eligibleAntecedent, nativeReply} from './model'
import {explanations, labels} from './labels'
import type {Confidence, Message, Status} from './types'

export function author(message: Message, pseudonyms: boolean) {
  if (!pseudonyms) return message.author_username || message.author_id
  let hash = 0
  for (const character of message.author_id) hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0
  return `Participant ${Math.abs(hash).toString(16).padStart(6, '0')}`
}
export function time(value?: string) {
  if (!value) return 'Time unavailable'
  const date = new Date(value)
  return Number.isNaN(+date) ? value : date.toLocaleString('en-US', {timeZone: 'UTC'}) + ' UTC'
}

export function MessageCard({model: m, message, selectable = false}: {model: AppModel; message: Message; selectable?: boolean}) {
  const selected = !!m.draft?.edges.some(edge => edge.target_message_id === message.message_id)
  const source = m.state?.messages.find(item => item.message_id === m.work)
  const eligible = !!source && eligibleAntecedent(source, message)
  const reply = nativeReply(m.state?.messages || [], message)
  const inComponent = m.state?.components.find(component => component.signature === m.component)?.message_ids.includes(message.message_id)
  return <article id={`message-${message.message_id}`} tabIndex={-1} className={`message-card${message.message_id === m.work ? ' source-message' : ''}${selected ? ' selected-message' : ''}${inComponent ? ' component-message' : ''}${m.focused === message.message_id ? ' focused-message' : ''}`} aria-label={`Message ${message.sequence}`}>
    <div className="between">
      <strong>#{message.sequence} · {author(message, m.pseudonyms)}</strong>
      <Label variant={message.requires_reply_annotation ? 'accent' : 'secondary'}>{message.requires_reply_annotation ? 'Target' : 'Context'}</Label>
    </div>
    <p className="muted small">{time(message.timestamp)}</p>
    {reply.id && <div className="native-reply">
      <Button size="small" variant="invisible" onClick={() => { m.inspected = message; m.changed() }}>Inspect Discord reply{reply.target ? ` to #${reply.target.sequence}` : ' outside interval'}</Button>
      <p className="message-text muted">{reply.target?.content || `Reference: ${reply.id}`}</p>
    </div>}
    <p className="message-text">{message.content || '[Message has no text]'}</p>
    <div className="actions">
      {selectable && eligible && <Button size="small" disabled={m.busy} onClick={() => { try { m.toggleLink(message.message_id) } catch (error) { m.report(error) } }} aria-pressed={selected}>{selected ? 'Remove antecedent' : 'Select antecedent'}</Button>}
      {message.requires_reply_annotation && message.message_id !== m.work && <Button size="small" disabled={m.busy} onClick={() => void m.run(async () => { await m.selectSource(message.message_id); m.tab = 'annotate' })}>Annotate #{message.sequence}</Button>}
      <Button size="small" variant="invisible" disabled={m.busy} onClick={() => { m.inspected = message; m.changed() }}>Metadata</Button>
      {m.state?.decisions[message.message_id] && <span className="muted small">{labels[m.state.decisions[message.message_id]!.source_status]}</span>}
    </div>
  </article>
}

export function Annotation({model: m}: {model: AppModel}) {
  const [streamQuery, setStreamQuery] = useState('')
  const [candidateQuery, setCandidateQuery] = useState('')
  const [nativeOnly, setNativeOnly] = useState(false)
  const [focusComponent, setFocusComponent] = useState(false)
  const [selectMode, setSelectMode] = useState(true)
  const [candidateIndex, setCandidateIndex] = useState(0)
  const candidateRef = useRef<HTMLInputElement>(null)
  const state = m.state!, draft = m.draft
  const source = state.messages.find(message => message.message_id === m.work)
  const component = state.components.find(component => component.signature === m.component)
  const candidates = source ? state.messages.filter(message => eligibleAntecedent(source, message) && [message.content, message.message_id, author(message, m.pseudonyms)].join(' ').toLowerCase().includes(candidateQuery.toLowerCase())).reverse() : []
  const filtered = state.messages.filter(message => (!nativeOnly || message.native_reply_to_message_id) && (!focusComponent || !component || component.message_ids.includes(message.message_id)) && [message.content, message.message_id, author(message, m.pseudonyms)].join(' ').toLowerCase().includes(streamQuery.toLowerCase()))

  useEffect(() => { setCandidateIndex(0) }, [candidateQuery, m.work])
  useEffect(() => {
    setStreamQuery(''); setNativeOnly(false); setFocusComponent(false)
  }, [m.revealVersion])
  useEffect(() => {
    document.getElementById(`message-${m.focused}`)?.scrollIntoView?.({block: 'center', behavior: 'smooth'})
  }, [m.focused, m.work, m.revealVersion, streamQuery, nativeOnly, focusComponent])

  function reveal(id: string) {
    setStreamQuery(''); setNativeOnly(false); setFocusComponent(false)
    m.reveal(id)
    requestAnimationFrame(() => document.getElementById(`message-${id}`)?.scrollIntoView?.({block: 'center', behavior: 'smooth'}))
  }
  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      const target = event.target
      if (m.busy || m.closing || m.modal || m.inspected || !(target instanceof HTMLElement) || target.closest('input,textarea,select,button,a,[role="separator"],[role="button"],[contenteditable="true"]')) return
      if (event.key === '?') { event.preventDefault(); m.modal = 'guide'; m.changed(); return }
      if (event.key === '/') { event.preventDefault(); candidateRef.current?.focus(); return }
      if (event.key === 'Enter') { event.preventDefault(); void m.run(() => m.confirm()); return }
      if ((event.ctrlKey || event.metaKey) && ['z', 'y'].includes(event.key.toLowerCase())) {
        event.preventDefault(); void m.run(() => m.undo(event.shiftKey || event.key.toLowerCase() === 'y')); return
      }
      if (event.ctrlKey || event.metaKey || event.altKey) return
      if (event.key === 'Escape') { event.preventDefault(); reveal(m.work); return }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault()
        const index = Math.max(0, Math.min(candidates.length - 1, candidateIndex + (event.key === 'ArrowDown' ? 1 : -1)))
        setCandidateIndex(index)
        if (candidates[index]) reveal(candidates[index].message_id)
      }
      if (event.key.toLowerCase() === 'l' && candidates[candidateIndex]) {
        event.preventDefault()
        try { m.toggleLink(candidates[candidateIndex].message_id) } catch (error) { m.report(error) }
      }
      if (['n', 'u'].includes(event.key.toLowerCase()) && !m.draft?.edges.length) {
        event.preventDefault(); m.edit(draft => { draft.source_status = event.key.toLowerCase() === 'n' ? 'new_conversation' : 'ambiguous' })
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  })

  if (!source || !draft) return <Flash>No target messages require annotation in this interval.</Flash>
  const targets = state.messages.filter(message => message.requires_reply_annotation)
  const targetIndex = targets.findIndex(message => message.message_id === m.work)
  const reply = nativeReply(state.messages, source)
  const incoming = state.messages.filter(message => message.native_reply_to_message_id === source.message_id)
  return <PageLayout containerWidth="full" padding="none" columnGap="normal">
    <PageLayout.Content as="div">
      <section className="stack stream-pane">
        <Heading as="h3" className="section-title">Read messages</Heading>
        <p className="muted">Chronological stream. Select earlier messages explicitly; inspecting replies never creates a human link.</p>
        <FormControl><FormControl.Label>Search messages</FormControl.Label><TextInput block value={streamQuery} onChange={event => setStreamQuery(event.target.value)} /></FormControl>
        <div className="actions">
          <Button size="small" aria-pressed={!selectMode} onClick={() => setSelectMode(!selectMode)}>{selectMode ? 'Explore without selecting' : 'Enable antecedent selection'}</Button>
          <Button size="small" onClick={() => reveal(m.work)}>Return to source</Button>
        </div>
        <FormControl><Checkbox checked={nativeOnly} onChange={event => setNativeOnly(event.target.checked)} /><FormControl.Label>Only messages with native replies</FormControl.Label></FormControl>
        {component && <FormControl><Checkbox checked={focusComponent} onChange={event => setFocusComponent(event.target.checked)} /><FormControl.Label>Focus selected conversation</FormControl.Label></FormControl>}
        <div className="stream scroll-region" aria-label="Chronological messages">
          {filtered.map(message => <MessageCard key={message.message_id} model={m} message={message} selectable={selectMode} />)}
          {!filtered.length && <p>No messages match the filters.</p>}
        </div>
      </section>
    </PageLayout.Content>
    <PageLayout.Pane position="end" width={{min: '320px', default: '420px', max: '640px'}} resizable widthStorageKey="discord.editorWidth" aria-label="Annotate source">
      <section className="editor scroll-region">
        <fieldset className="stack" disabled={m.busy}>
          <Heading as="h3" className="section-title">Annotate source</Heading>
          <div className="between"><strong>Target {targetIndex + 1} of {targets.length}</strong><span role="status" aria-live="polite" className={m.saveError ? 'error-text' : 'muted'}>{m.saveError ? 'Draft save failed' : m.dirty ? 'Saving draft...' : 'Saved locally'}</span></div>
          {m.saveError && <Button onClick={() => void m.run(() => m.flush())}>Retry saving draft</Button>}
          <div className="actions"><Button size="small" disabled={targetIndex === 0} onClick={() => void m.run(() => m.selectSource(targets[targetIndex - 1]!.message_id))}>Previous target</Button><Button size="small" disabled={targetIndex === targets.length - 1} onClick={() => void m.run(() => m.selectSource(targets[targetIndex + 1]!.message_id))}>Next target</Button><Button size="small" onClick={() => { m.paused = !m.paused; m.changed() }}>{m.paused ? 'Resume timer' : 'Pause timer'}</Button></div>
          <div className="panel"><strong>#{source.sequence} · {author(source, m.pseudonyms)}</strong><p className="message-text">{source.content || '[Message has no text]'}</p></div>
          <Heading as="h4" className="section-title">Native Discord reply evidence</Heading>
          {reply.id ? <div className="native-reply stack">
            <p>{reply.target ? `Reference to #${reply.target.sequence}: ${reply.target.content}` : `Reference ${reply.id} is outside this interval.`}</p>
            <div className="actions"><Button size="small" onClick={() => { m.inspected = source; m.changed() }}>Inspect reply</Button>
              {reply.target && <Button size="small" onClick={() => reveal(reply.target!.message_id)}>Locate in stream</Button>}
              <Button size="small" disabled={!reply.eligible || draft.edges.some(edge => edge.target_message_id === reply.id)} onClick={() => { try { m.addNative(source) } catch (error) { m.report(error) } }}>Add as antecedent</Button></div>
            {!reply.eligible && reply.target && <p className="error-text">This reference is not an eligible earlier antecedent.</p>}
            <p className="muted small">Evidence only. Adding changes the draft, not the confirmed annotation.</p>
          </div> : <p className="muted">No direct reply is recorded. You can still identify a relation from context.</p>}
          {!!incoming.length && <div className="stack"><p className="muted">Later messages replying to this source are context, not antecedents:</p><div className="actions">{incoming.map(message => <Button key={message.message_id} size="small" onClick={() => reveal(message.message_id)}>View reply #{message.sequence}</Button>)}</div></div>}
          <Heading as="h4" className="section-title">Selected antecedents ({draft.edges.length})</Heading>
          {draft.edges.map(edge => {
            const target = state.messages.find(message => message.message_id === edge.target_message_id)!
            return <div className="panel stack" key={edge.target_message_id}>
              <strong>#{target.sequence} · {author(target, m.pseudonyms)}</strong><p className="message-text">{target.content}</p>
              <FormControl><Checkbox checked={edge.ambiguous} onChange={event => m.edit(draft => { draft.edges.find(item => item.target_message_id === edge.target_message_id)!.ambiguous = event.target.checked })} /><FormControl.Label>Uncertain link to #{target.sequence}</FormControl.Label></FormControl>
              <div className="actions"><Button size="small" onClick={() => reveal(target.message_id)}>Locate #{target.sequence}</Button><Button size="small" onClick={() => m.toggleLink(target.message_id)}>Remove #{target.sequence}</Button></div>
            </div>
          })}
          <FormControl><FormControl.Label>Search earlier antecedents</FormControl.Label><TextInput ref={candidateRef} block value={candidateQuery} onChange={event => setCandidateQuery(event.target.value)} /></FormControl>
          <div className="candidate-list">
            {candidates.map((message, index) => <div key={message.message_id} className={`candidate${index === candidateIndex ? ' candidate-current' : ''}`}>
              <Button block size="small" aria-pressed={draft.edges.some(edge => edge.target_message_id === message.message_id)} onClick={() => m.toggleLink(message.message_id)}>
                {draft.edges.some(edge => edge.target_message_id === message.message_id) ? 'Remove' : 'Add'} #{message.sequence} · {message.content.slice(0, 100) || '[No text]'}{message.message_id === reply.id ? ' · Native reply' : ''}
              </Button>
            </div>)}
            {!candidates.length && <p className="muted">No eligible earlier messages match.</p>}
          </div>
          <FormControl><FormControl.Label>Decision</FormControl.Label>
            <Select block value={draft.source_status} onChange={event => m.edit(draft => { draft.source_status = event.target.value as Status })}>
              {Object.entries(labels).map(([status, title]) => <Select.Option key={status} value={status} disabled={draft.edges.length > 0 && status !== 'complete'}>{title}</Select.Option>)}
            </Select><FormControl.Caption>{explanations[draft.source_status]}</FormControl.Caption>
          </FormControl>
          <FormControl><FormControl.Label>Confidence</FormControl.Label><Select block value={draft.confidence} onChange={event => m.edit(draft => { draft.confidence = event.target.value as Confidence; draft.edges.forEach(edge => { edge.confidence = draft.confidence }) })}>
            <Select.Option value="high">High</Select.Option><Select.Option value="medium">Medium</Select.Option><Select.Option value="low">Low</Select.Option>
          </Select></FormControl>
          <FormControl><Checkbox checked={draft.unresolved_additional_relation} onChange={event => m.edit(draft => { draft.unresolved_additional_relation = event.target.checked })} /><FormControl.Label>An additional relation remains unresolved</FormControl.Label></FormControl>
          {draft.unresolved_additional_relation && <FormControl><FormControl.Label>Uncertainty reason</FormControl.Label><Textarea block value={draft.unresolved_reason} onChange={event => m.edit(draft => { draft.unresolved_reason = event.target.value })} /></FormControl>}
          <FormControl required={state.session.kind === 'adjudication'}><FormControl.Label>{state.session.kind === 'adjudication' ? 'Adjudication rationale' : 'Decision notes'}</FormControl.Label><Textarea block value={draft.notes} onChange={event => m.edit(draft => { draft.notes = event.target.value })} /></FormControl>
          <Button variant="primary" disabled={draft.source_status === 'pending'} onClick={() => void m.run(() => m.confirm())}>Confirm decision and advance</Button>
          <div className="actions"><Button size="small" onClick={() => void m.run(() => m.discardDraft())}>Discard draft</Button><Button size="small" onClick={() => void m.run(() => m.undo())}>Undo</Button><Button size="small" onClick={() => void m.run(() => m.undo(true))}>Redo</Button></div>
          <p className="muted small">Drafts are resumable edits. Only confirmed decisions become labels.</p>
        </fieldset>
      </section>
    </PageLayout.Pane>
  </PageLayout>
}
