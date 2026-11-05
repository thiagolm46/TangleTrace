import {useState} from 'react'
import {ActionList, Button, Checkbox, Flash, FormControl, Heading, Label, Select} from '@primer/react'
import {DataTable, Table} from '@primer/react/experimental'
import {AppModel} from './model'
import {MessageCard} from './Annotation'
import {checklistLabels, labels} from './labels'
import type {Decision} from './types'

export function Conversations({model: m}: {model: AppModel}) {
  const state = m.state!
  const component = state.components.find(component => component.signature === m.component) || state.components[0]
  return <section className="stack">
    <Heading as="h3" className="section-title">Conversations observed in this interval</Heading>
    <Flash>Components use confirmed, non-ambiguous human links. Native replies are evidence only. Conversation boundaries remain unverified.</Flash>
    <div className="conversation-layout">
      <div className="stack">
        <ActionList aria-label="Derived conversations">
          {state.components.map((item, index) => <ActionList.Item key={item.signature} active={component?.signature === item.signature} onSelect={() => { m.component = item.signature; m.changed() }}>
            Conversation {index + 1}
            <ActionList.Description variant="block">{item.message_ids.length} messages · {item.participants} participants · {item.reviewed ? 'Reviewed' : 'Needs review'}</ActionList.Description>
          </ActionList.Item>)}
        </ActionList>
        <p>{state.unassigned.length} messages outside components, including context and no-link decisions. These are not automatically individual conversations.</p>
        <Button onClick={() => void m.run(() => m.changeTab('annotate'))}>Review full stream</Button>
      </div>
      {component ? <div className="stack">
        <div className="between"><strong>{component.message_ids.length} messages · {component.participants} participants</strong>
          <Button variant="primary" disabled={m.busy || component.reviewed} onClick={() => void m.run(() => m.reviewComponent(component.signature))}>{component.reviewed ? 'Reviewed' : 'Mark as reviewed'}</Button>
        </div>
        <span className="muted small">{component.conversation_id}</span>
        {component.includes_context && <p className="muted">Includes antecedents imported as context, not annotated sources.</p>}
        <Button onClick={() => void m.run(async () => { m.component = component.signature; m.reveal(component.message_ids[0]!); await m.changeTab('annotate') })}>Open conversation in stream</Button>
        <div className="scroll-region">{component.message_ids.map(id => <MessageCard key={id} model={m} message={state.messages.find(message => message.message_id === id)!} />)}</div>
      </div> : <p>No conversations yet. Confirm links or explicitly record a new conversation.</p>}
    </div>
  </section>
}

export function Review({model: m}: {model: AppModel}) {
  const state = m.state!
  const uncertain = Object.values(state.decisions).filter(decision => ['ambiguous', 'outside_context'].includes(decision.source_status) || decision.unresolved_additional_relation || decision.edges.some(edge => edge.ambiguous))
  const counts = Object.entries(labels).map(([status, title]) => [title, Object.values(state.decisions).filter(decision => decision.source_status === status).length] as const)
  const hasDrafts = m.dirty || Object.keys(state.drafts).length > 0
  const complete = Object.keys(checklistLabels).every(key => m.checklist[key])
  return <section className="stack">
    <Heading as="h3" className="section-title">Review the full observed interval</Heading>
    <p>Inspect interleaving between conversations, unassigned targets, and uncertainty. Validation applies only to this sample and revision.</p>
    <div className="stats">
      <Stat label="Targets confirmed" value={`${state.progress.confirmed} / ${state.progress.total}`} />
      <Stat label="Conversations reviewed" value={`${state.components.filter(component => component.reviewed).length} / ${state.components.length}`} />
      <Stat label="Outside components" value={state.unassigned.length} />
      <Stat label="Uncertain cases" value={uncertain.length} />
    </div>
    <div className="review-layout">
      <section className="panel stack">
        <Heading as="h4" className="section-title">Inspection checklist</Heading>
        {Object.entries(checklistLabels).map(([key, title]) => <FormControl key={key} disabled={m.busy}><Checkbox checked={!!m.checklist[key]} onChange={event => { m.checklist[key] = event.target.checked; m.changed() }} /><FormControl.Label>{title}</FormControl.Label></FormControl>)}
        <Flash variant={state.review_blockers.length || hasDrafts ? 'warning' : 'default'}>{state.review_blockers.join(' · ') || (hasDrafts ? 'Confirm or discard open drafts before validation.' : 'No structural blockers. Complete the checklist before validating.')}</Flash>
        <Button variant="primary" disabled={m.busy || !complete || hasDrafts || state.review_blockers.length > 0} onClick={() => void m.run(() => m.validate())}>Validate interval review</Button>
        {state.validated && !hasDrafts && <Label variant="success">Interval validated</Label>}
        <p className="muted">A validated individual annotation remains an individual annotation, not an adjudicated gold standard.</p>
      </section>
      <section className="stack">
        <div className="panel stack">
          <Heading as="h4" className="section-title">Recorded decisions</Heading>
          <div className="actions">{counts.map(([title, count]) => <Label key={title}>{title}: {count}</Label>)}</div>
          <div className="actions"><Button disabled={m.busy} onClick={() => void m.run(() => m.changeTab('annotate'))}>Review full stream</Button><Button disabled={m.busy} onClick={() => void m.run(() => m.showHistory())}>Action history</Button><Button disabled={m.busy} onClick={() => void m.run(() => m.backup())}>Create backup</Button></div>
          <p className="muted">Confirmed active time: {Math.round(state.progress.active_ms / 60000)} min. Pauses and inactivity longer than 60 seconds are excluded.</p>
          {m.backupPath && <p className="path">Backup: {m.backupPath}</p>}
        </div>
        <Heading as="h4" className="section-title">Pending and unassigned targets</Heading>
        <ActionList aria-label="Targets to inspect">
          {state.messages.filter(message => message.requires_reply_annotation && (state.unassigned.includes(message.message_id) || state.decisions[message.message_id]?.source_status === 'pending')).map(message => <ActionList.Item key={message.message_id} disabled={m.busy} onSelect={() => void m.run(async () => { await m.selectSource(message.message_id); m.tab = 'annotate' })}>
            #{message.sequence} · {message.content || '[No text]'}
            <ActionList.Description variant="block">{labels[state.decisions[message.message_id]!.source_status]}</ActionList.Description>
          </ActionList.Item>)}
        </ActionList>
      </section>
    </div>
  </section>
}

function Stat({label, value}: {label: string; value: string | number}) {
  return <div className="panel"><strong className="stat-value">{value}</strong><span className="muted">{label}</span></div>
}
function percentage(value: number | null) { return value === null ? 'Not available' : `${(value * 100).toFixed(1)}%` }
function DecisionSummary({decision}: {decision: Decision}) {
  return <div><Label>{labels[decision.source_status]}</Label><p className="small">{decision.edges.map(edge => `${edge.target_message_id}${edge.ambiguous ? ' (uncertain)' : ''}`).join(', ') || 'No link recorded'}</p></div>
}

export function Compare({model: m}: {model: AppModel}) {
  const [left, setLeft] = useState(m.comparison?.left.id || m.state!.session.id)
  const [right, setRight] = useState(m.comparison?.right.id || m.sessions.find(session => session.id !== left)?.id || '')
  const comparison = m.comparison
  return <section className="stack">
    <Heading as="h3" className="section-title">Compare independent sessions</Heading>
    <p>Unresolved decisions, outside-context antecedents, ambiguous edges, and additional uncertainty are excluded from agreement measures. Original sessions are preserved.</p>
    <div className="comparison-controls">
      <FormControl disabled={m.busy}><FormControl.Label>First session</FormControl.Label><Select block value={left} onChange={event => setLeft(event.target.value)}>{m.sessions.map(session => <Select.Option key={session.id} value={session.id}>{session.annotator_id} · {session.label} · r{session.graph_revision}</Select.Option>)}</Select></FormControl>
      <FormControl disabled={m.busy}><FormControl.Label>Second session</FormControl.Label><Select block value={right} onChange={event => setRight(event.target.value)}><Select.Option value="">Choose session</Select.Option>{m.sessions.map(session => <Select.Option key={session.id} value={session.id}>{session.annotator_id} · {session.label} · r{session.graph_revision}</Select.Option>)}</Select></FormControl>
      <Button variant="primary" disabled={m.busy || !left || !right || left === right} onClick={() => void m.run(() => m.compare(left, right))}>Compare</Button>
      <Button disabled={m.busy || !comparison || comparison.left.kind !== 'single_annotator' || comparison.right.kind !== 'single_annotator' || comparison.left.annotator_id === comparison.right.annotator_id} onClick={() => { m.modal = 'adjudicate'; m.changed() }}>Create adjudication</Button>
    </div>
    {comparison ? <>
      <div className="stats">
        <Stat label="Comparable sources" value={comparison.comparable_sources} />
        <Stat label="Matching decisions" value={percentage(comparison.exact_decision_agreement)} />
        <Stat label="Link Jaccard" value={percentage(comparison.link_jaccard)} />
        <Stat label="Grouped-pair Jaccard" value={percentage(comparison.component_pair_jaccard)} />
      </div>
      <p className="muted">Grouping uses {comparison.component_comparable_nodes} comparable targets present in both graphs. Not available means an empty denominator.</p>
      <Table.Container>
        <Table.Title as="h4" id="comparison-title">Decision comparison</Table.Title>
        <DataTable aria-labelledby="comparison-title" data={comparison.rows.map(row => ({...row, id: row.message_id}))} columns={[
          {header: 'Target message', field: 'message_id', renderCell: row => <Button variant="invisible" disabled={m.busy} onClick={() => void m.run(async () => { await m.selectSource(row.message_id); m.tab = 'annotate' })}>#{m.state!.messages.find(message => message.message_id === row.message_id)?.sequence} · {row.message_id}</Button>},
          {header: comparison.left.annotator_id, field: 'left', renderCell: row => <DecisionSummary decision={row.left} />},
          {header: comparison.right.annotator_id, field: 'right', renderCell: row => <DecisionSummary decision={row.right} />},
          {header: 'Comparison', field: 'agree', renderCell: row => <Label variant={!row.comparable ? 'secondary' : row.agree ? 'success' : 'attention'}>{!row.comparable ? 'Not comparable' : row.agree ? 'Agreement' : 'Disagreement'}</Label>},
        ]} />
      </Table.Container>
    </> : <Flash>Select two sessions for this interval to inspect differences. Adjudication requires two distinct annotators.</Flash>}
  </section>
}
