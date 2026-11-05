import {useEffect, useState, useSyncExternalStore} from 'react'
import {ActionList, Button, Flash, FormControl, Heading, PageLayout, ProgressBar, Select, Spinner, TextInput, UnderlineNav} from '@primer/react'
import {listen} from '@tauri-apps/api/event'
import {AppModel} from './model'
import type {Tab} from './model'
import {Annotation} from './Annotation'
import {Conversations, Review, Compare} from './Stages'
import {Dialogs, ImportForm} from './Dialogs'

const tabs: [Tab, string][] = [['annotate', '1. Annotate'], ['conversations', '2. Conversations'], ['review', '3. Validate interval'], ['compare', 'Compare sessions']]

export function App({model: m}: {model: AppModel}) {
  useSyncExternalStore(m.subscribe, m.snapshot)
  const [sidebar, setSidebar] = useState(localStorage.getItem('discord.sidebarCollapsed') !== 'true')

  useEffect(() => {
    let disposed = false
    let unlisten: (() => void) | undefined
    void listen('desktop-close-requested', () => { void m.close() }).then(cleanup => {
      if (disposed) cleanup()
      else unlisten = cleanup
    }).catch(error => m.report(error))
    void m.boot().catch(error => m.report(error))
    const timer = setInterval(() => m.tick(), 1000)
    const activity = () => { m.lastActivity = Date.now() }
    const unload = (event: BeforeUnloadEvent) => {
      m.persistTime()
      if (m.dirty || m.saveError) { event.preventDefault(); event.returnValue = '' }
    }
    document.addEventListener('keydown', activity)
    document.addEventListener('pointerdown', activity)
    window.addEventListener('beforeunload', unload)
    return () => {
      disposed = true
      unlisten?.()
      clearInterval(timer)
      m.dispose()
      document.removeEventListener('keydown', activity)
      document.removeEventListener('pointerdown', activity)
      window.removeEventListener('beforeunload', unload)
    }
  }, [m])

  function show(modal: AppModel['modal']) { m.modal = modal; m.changed() }
  const validated = m.state?.validated && !m.dirty && Object.keys(m.state.drafts).length === 0
  return <div className="app-shell" aria-busy={m.busy || m.loading} inert={m.closing || undefined}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="app-header">
      <div><Heading as="h1" className="app-title">TangleTrace BETWEEN</Heading><span className="muted">Reply-Link Annotation &amp; Review</span></div>
      <nav className="actions" aria-label="Application">
        <Button disabled={m.busy || m.loading} onClick={() => show('files')}>My files</Button>
        <Button disabled={m.busy || m.loading} onClick={() => show('guide')}>Annotation guide</Button>
        <Button disabled={m.busy || m.loading || !m.config} onClick={() => show('import')}>Open sample</Button>
        <Button disabled={m.busy || m.loading} onClick={() => show('identity')}>{m.annotator || 'Set annotator'}</Button>
      </nav>
    </header>
    <div className="notifications">
      {m.error && <Flash variant="danger" role="alert"><div className="between"><span>{m.error}</span><Button size="small" onClick={() => { m.error = ''; m.changed() }}>Dismiss error</Button></div></Flash>}
      {m.notice && <Flash variant="success" role="status"><div className="between"><span>{m.notice}</span><Button size="small" onClick={() => { m.notice = ''; m.changed() }}>Dismiss</Button></div></Flash>}
      {m.busy && <div role="status" className="actions"><Spinner size="small" />{m.importProgress || 'Working locally...'}</div>}
    </div>
    {m.loading ? <main id="main-content" className="welcome"><Spinner /><p>Opening local workspace...</p></main>
      : !m.config ? <main id="main-content" className="welcome stack">
        <Heading as="h2">Could not open the workspace</Heading>
        <p>Check local dependencies, folder permissions, and whether another instance is using the database.</p>
        <div className="actions"><Button disabled={m.busy} onClick={() => void m.run(() => m.boot())}>Try again</Button><Button disabled={m.busy} onClick={() => void m.run(() => m.switchWorkspace())}>Choose another workspace</Button></div>
      </main>
      : !m.imports.length ? <main id="main-content" className="welcome stack">
        <Heading as="h2">Understand the context. Record your decision.</Heading>
        <p>Decide which earlier messages a target replies to. Conversations are reconstructed from the links you confirm. All data stay on this computer.</p>
        <div className="welcome-grid">
          <section className="panel stack"><Heading as="h3">1. Identify your work</Heading>
            <p>Reuse a stable identifier to resume your independent annotation sessions.</p>
            <p>{m.annotator ? `Current annotator: ${m.annotator}` : 'An identifier is required before annotation.'}</p>
            <Button onClick={() => show('identity')}>{m.annotator ? 'Change identity' : 'Set annotator'}</Button>
            <Heading as="h3">Your local workspace</Heading><p className="path">{m.config.workspace}</p>
            <Button onClick={() => show('files')}>View database, backups, and results</Button>
          </section>
          <section className="panel stack"><Heading as="h3">2. Open sampled data</Heading><ImportForm model={m} /></section>
        </div>
      </main> : <div className="workspace-root">
        <div className="workspace-toolbar between">
          <Button size="small" onClick={() => { setSidebar(!sidebar); localStorage.setItem('discord.sidebarCollapsed', String(sidebar)) }}>{sidebar ? 'Hide intervals' : 'Show intervals'}</Button>
          <span className="muted">Sampled intervals, not complete channels. Data remain local.</span>
        </div>
        <PageLayout containerWidth="full" padding="normal" columnGap="normal">
          <PageLayout.Pane hidden={!sidebar} position="start" width={{min: '220px', default: '260px', max: '380px'}} resizable widthStorageKey="discord.intervalWidth" aria-label="Choose interval">
            <Intervals model={m} />
          </PageLayout.Pane>
          <PageLayout.Content>
            <div id="main-content">
              {!m.state ? <div className="panel stack"><Heading as="h2">Choose an interval</Heading><p>Select a sampled window to open or resume a session.</p></div> : <>
                <div className="session-heading between">
                  <div><Heading as="h2" className="section-title">{m.state.window.guild_name} / #{m.state.window.channel_name}</Heading>
                    <p className="muted">{m.state.session.annotator_id} · {m.state.session.label} · Revision {m.state.session.graph_revision}{m.state.session.kind === 'adjudication' ? ' · Adjudication' : ''}</p>
                  </div>
                  <div className="actions">
                    <Button disabled={m.busy} onClick={() => void m.run(async () => { await m.loadSessions(); show('sessions') })}>Sessions</Button>
                    <Button disabled={m.busy} onClick={() => void m.run(async () => { await m.flush(); m.lastExport = null; show('export') })}>Export</Button>
                  </div>
                </div>
                <div className="progress-summary"><span>{m.state.progress.confirmed} / {m.state.progress.total} targets confirmed{validated ? ' · Interval validated' : ''}</span>
                  <ProgressBar progress={m.state.progress.total ? 100 * m.state.progress.confirmed / m.state.progress.total : 0} aria-label="Confirmed targets" />
                </div>
                <UnderlineNav aria-label="Annotation workflow">
                  {tabs.map(([tab, title]) => <UnderlineNav.Item key={tab} as="button" type="button" aria-current={m.tab === tab ? 'page' : undefined} disabled={m.busy} onSelect={() => void m.run(() => m.changeTab(tab))}>{title}</UnderlineNav.Item>)}
                </UnderlineNav>
                <div className="stage">
                  {m.tab === 'annotate' && <Annotation model={m} />}
                  {m.tab === 'conversations' && <Conversations model={m} />}
                  {m.tab === 'review' && <Review model={m} />}
                  {m.tab === 'compare' && <Compare model={m} />}
                </div>
              </>}
            </div>
          </PageLayout.Content>
        </PageLayout>
      </div>}
    <Dialogs model={m} />
  </div>
}

function Intervals({model: m}: {model: AppModel}) {
  const [query, setQuery] = useState('')
  const filtered = m.windows.filter(window => [window.guild_name, window.channel_name, window.annotation_id, window.period].join(' ').toLowerCase().includes(query.toLowerCase()))
  return <div className="stack intervals">
    <Heading as="h2" className="section-title">Choose interval</Heading>
    <FormControl disabled={m.busy}><FormControl.Label>Sampling run</FormControl.Label>
      <Select block value={m.importId} onChange={event => void m.run(() => m.chooseImport(event.target.value))}>
        {m.imports.map(item => <Select.Option key={item.id} value={item.id}>{item.name}</Select.Option>)}
      </Select>
    </FormControl>
    <FormControl><FormControl.Label>Search intervals</FormControl.Label><TextInput block value={query} onChange={event => setQuery(event.target.value)} placeholder="Channel, server, or ID" /></FormControl>
    <span className="muted">{filtered.length} intervals</span>
    <div className="interval-list"><ActionList aria-label="Sampled intervals">
      {filtered.map(window => {
        const session = window.sessions.find(session => session.label === m.label)
        return <ActionList.Item key={window.sample_id} active={m.state?.session.sample_id === window.sample_id} disabled={m.busy} onSelect={() => void m.run(() => m.openSession(window.sample_id))}>
          #{window.channel_name}
          <ActionList.Description variant="block">{window.guild_name} · {window.annotated_message_count} targets · {window.context_message_count} context<br />{session ? `${session.confirmed || 0} confirmed${session.validated ? ' · Validated' : ''}` : 'Not started'}</ActionList.Description>
        </ActionList.Item>
      })}
    </ActionList></div>
    {!filtered.length && <p>No matching intervals.</p>}
    <Button size="small" onClick={() => { m.modal = 'provenance'; m.changed() }}>Sample provenance</Button>
  </div>
}
