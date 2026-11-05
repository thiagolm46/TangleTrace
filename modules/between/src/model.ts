import {native, request} from './transport'
import type {Backend} from './transport'
import type {AnnotationState, Comparison, Config, Decision, ExportResult, HistoryEvent, ImportRecord, Message, SampleWindow, Session} from './types'

export type Tab = 'annotate' | 'conversations' | 'review' | 'compare'
export type Modal = 'identity' | 'import' | 'files' | 'guide' | 'sessions' | 'history' | 'provenance' | 'export' | 'adjudicate' | 'close' | null
const copy = <T,>(value: T): T => structuredClone(value)

export function eligibleAntecedent(source: Message, target: Message): boolean {
  return target.sequence < source.sequence && target.channel_id === source.channel_id && target.guild_id === source.guild_id
}

export function nativeReply(messages: Message[], source: Message) {
  const id = source.native_reply_to_message_id
  const target = messages.find(message => message.message_id === id)
  return {id, target, eligible: !!target && eligibleAntecedent(source, target)}
}

export class AppModel {
  config: Config | null = null
  imports: ImportRecord[] = []
  importId = localStorage.getItem('discord.import') || ''
  windows: SampleWindow[] = []
  state: AnnotationState | null = null
  annotator = localStorage.getItem('discord.annotator') || ''
  label = localStorage.getItem('discord.label') || 'Primary'
  pseudonyms = localStorage.getItem('discord.pseudonyms') !== 'false'
  tab: Tab = 'annotate'
  modal: Modal = null
  inspected: Message | null = null
  work = ''
  focused = ''
  revealVersion = 0
  draft: Decision | null = null
  dirty = false
  saveError = false
  busy = false
  closing = false
  loading = true
  error = ''
  notice = ''
  importProgress = ''
  component = ''
  checklist: Record<string, boolean> = {}
  sessions: Session[] = []
  comparison: Comparison | null = null
  history: HistoryEvent[] = []
  lastExport: ExportResult | null = null
  backupPath = ''
  paused = false
  activeMs = 0
  lastActivity = Date.now()
  undoDraft: Decision[] = []
  redoDraft: Decision[] = []
  private version = 0
  private listeners = new Set<() => void>()
  private timer: ReturnType<typeof setTimeout> | undefined
  private saving: Promise<void> | null = null
  private backend: Backend

  constructor(backend: Backend = request) { this.backend = backend }
  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => { this.listeners.delete(listener) }
  }
  snapshot = () => this.version
  changed = () => { this.version++; this.listeners.forEach(listener => listener()) }
  reveal(id: string) {
    this.focused = id
    this.revealVersion++
    this.changed()
  }
  report(error: unknown) {
    this.error = error instanceof Error ? error.message : String(error)
    this.changed()
  }
  async run(action: () => Promise<unknown>) {
    if (this.busy || this.closing) return
    this.busy = true
    this.error = ''
    this.changed()
    try { await action() } catch (error) { this.report(error) }
    finally { this.busy = false; this.changed() }
  }
  async boot() {
    this.loading = true
    this.changed()
    try {
      this.config = await this.backend('config', {})
      this.imports = await this.backend('imports', {})
      if (!this.imports.some(item => item.id === this.importId)) this.importId = this.imports[0]?.id || ''
      await this.refreshWindows()
      const previous = localStorage.getItem('discord.session')
      if (previous && this.annotator) {
        const state = await this.backend('state', {session_id: previous})
        if (state.session.annotator_id === this.annotator && state.session.import_id === this.importId) this.setState(state)
      }
    } finally { this.loading = false; this.changed() }
  }
  async refreshWindows() {
    this.windows = this.importId ? await this.backend('windows', {import_id: this.importId, annotator_id: this.annotator}) : []
  }
  revision() {
    if (!this.state) throw new Error('Open an annotation session first.')
    return {session_id: this.state.session.id, expected_revision: this.state.session.graph_revision}
  }
  private timeKey() { return this.state && this.work ? `discord.time.${this.state.session.id}.${this.work}` : '' }
  persistTime() {
    const key = this.timeKey()
    if (key) localStorage.setItem(key, String(this.activeMs))
  }
  tick() {
    if (this.state && !this.paused && !this.busy && !this.closing && !document.hidden && this.tab === 'annotate' && Date.now() - this.lastActivity < 60000) {
      this.activeMs += 1000
      if (this.activeMs % 5000 === 0) this.persistTime()
    }
  }
  private setState(state: AnnotationState, preferred?: string) {
    if (state.session.id !== this.state?.session.id || state.session.graph_revision !== this.state?.session.graph_revision) this.comparison = null
    this.state = state
    const work = preferred || state.session.cursor || ''
    this.work = state.decisions[work] ? work : state.pending[0] || Object.keys(state.decisions)[0] || ''
    this.draft = this.work ? copy(state.drafts[this.work]?.decision || state.decisions[this.work]!) : null
    this.activeMs = Math.max(0, Number(localStorage.getItem(this.timeKey()) || 0))
    this.lastActivity = Date.now()
    this.focused = this.work
    this.undoDraft = []
    this.redoDraft = []
    this.dirty = false
    this.saveError = false
    this.checklist = {}
    if (!state.components.some(component => component.signature === this.component)) this.component = ''
    localStorage.setItem('discord.session', state.session.id)
    this.changed()
  }
  async chooseImport(id: string) {
    await this.flush()
    this.persistTime()
    this.importId = id
    this.state = null
    this.work = ''
    this.draft = null
    this.comparison = null
    this.component = ''
    this.lastExport = null
    localStorage.setItem('discord.import', id)
    localStorage.removeItem('discord.session')
    await this.refreshWindows()
    this.changed()
  }
  async openSession(sample: string, id?: string) {
    await this.flush()
    this.persistTime()
    if (!this.annotator) { this.modal = 'identity'; this.changed(); return }
    const session = id ? {id} : await this.backend('open_session', {
      import_id: this.importId, sample_id: sample, annotator_id: this.annotator, label: this.label,
    })
    const state = await this.backend('state', {session_id: session.id})
    this.setState(state)
    this.component = ''
    this.comparison = null
    this.lastExport = null
    this.tab = 'annotate'
    this.modal = null
  }
  async selectSource(id: string) {
    if (!this.state?.decisions[id]) throw new Error('Only target messages can receive a source decision.')
    await this.flush()
    this.persistTime()
    await this.backend('cursor', {session_id: this.state.session.id, source_id: id})
    this.setState(this.state, id)
  }
  edit(update: (draft: Decision) => void) {
    if (!this.draft || this.busy || this.closing) return
    const next = copy(this.draft)
    update(next)
    if (JSON.stringify(next) === JSON.stringify(this.draft)) return
    this.undoDraft.push(copy(this.draft))
    if (this.undoDraft.length > 200) this.undoDraft.shift()
    this.redoDraft = []
    this.draft = next
    this.schedule()
  }
  private schedule() {
    this.dirty = true
    this.saveError = false
    this.checklist = {}
    this.lastActivity = Date.now()
    clearTimeout(this.timer)
    this.timer = setTimeout(() => { void this.flush().catch(error => this.report(error)) }, 350)
    this.changed()
  }
  async flush(): Promise<void> {
    clearTimeout(this.timer)
    if (!this.saving) {
      if (!this.dirty || !this.draft || !this.state) return
      this.saving = this.saveDrafts()
    }
    const saving = this.saving
    try { await saving } finally { if (this.saving === saving) this.saving = null }
    if (this.dirty) await this.flush()
  }
  private async saveDrafts() {
    while (this.dirty && this.draft && this.state) {
      const state = this.state, source = this.work, decision = copy(this.draft)
      this.dirty = false
      try {
        const result = await this.backend('draft', {
          ...this.revision(), source_id: source, decision,
          expected_draft_updated: state.drafts[source]?.updated_at || null,
        })
        if (result.updated_at) state.drafts[source] = {decision, updated_at: result.updated_at, base_revision: state.session.graph_revision}
        else delete state.drafts[source]
        this.saveError = false
      } catch (error) {
        this.dirty = true
        this.saveError = true
        throw error
      } finally { this.changed() }
    }
  }
  toggleLink(id: string) {
    const source = this.state?.messages.find(message => message.message_id === this.work)
    const target = this.state?.messages.find(message => message.message_id === id)
    if (!source || !target || !eligibleAntecedent(source, target)) throw new Error('Select an earlier message in the same channel and server.')
    this.edit(draft => {
      const index = draft.edges.findIndex(edge => edge.target_message_id === id)
      if (index >= 0) draft.edges.splice(index, 1)
      else {
        draft.edges.push({target_message_id: id, relation: 'reply', ambiguous: false, confidence: draft.confidence, notes: ''})
        draft.edges.sort((a, b) => this.state!.messages.find(m => m.message_id === a.target_message_id)!.sequence - this.state!.messages.find(m => m.message_id === b.target_message_id)!.sequence)
        draft.source_status = 'complete'
      }
    })
  }
  addNative(source: Message) {
    if (source.message_id !== this.work) throw new Error('Select this message as the annotation source first.')
    const reply = nativeReply(this.state?.messages || [], source)
    if (!reply.eligible || !reply.target) throw new Error('The native reference is not available as an earlier antecedent in this interval.')
    if (!this.draft?.edges.some(edge => edge.target_message_id === reply.id)) this.toggleLink(reply.target.message_id)
  }
  async confirm() {
    if (!this.draft || this.draft.source_status === 'pending') throw new Error('Choose a decision before confirming.')
    await this.flush()
    const current = this.work, state = this.state!
    const result = await this.backend('confirm', {
      ...this.revision(), source_id: current, decision: copy(this.draft), active_ms: this.activeMs,
      expected_draft_updated: state.drafts[current]?.updated_at || null,
    })
    localStorage.removeItem(this.timeKey())
    const sourceIndex = result.messages.findIndex(message => message.message_id === current)
    const next = result.messages.slice(sourceIndex + 1).find(message => result.decisions[message.message_id]?.source_status === 'pending')
    this.setState(result, next?.message_id || result.pending[0] || current)
    await this.backend('cursor', {session_id: result.session.id, source_id: this.work})
    await this.refreshWindows()
    this.notice = result.pending.length ? 'Decision confirmed.' : 'All targets confirmed. Review conversations and validate the interval.'
  }
  async discardDraft() {
    clearTimeout(this.timer)
    if (this.saving) await this.saving
    if (!this.state) return
    await this.backend('discard_draft', {
      session_id: this.state.session.id, source_id: this.work,
      expected_draft_updated: this.state.drafts[this.work]?.updated_at || null,
    })
    delete this.state.drafts[this.work]
    this.setState(this.state, this.work)
    this.notice = 'Draft discarded. The confirmed decision is preserved.'
  }
  async undo(redo = false) {
    const from = redo ? this.redoDraft : this.undoDraft
    const to = redo ? this.undoDraft : this.redoDraft
    const previous = from.pop()
    if (previous && this.draft) {
      to.push(copy(this.draft))
      this.draft = previous
      this.schedule()
      return
    }
    if (this.dirty || this.state?.drafts[this.work]) throw new Error('Confirm or discard this draft before changing confirmed history.')
    const state = await this.backend(redo ? 'redo' : 'undo', this.revision())
    this.setState(state, this.work)
    await this.refreshWindows()
    this.notice = redo ? 'Confirmation redone.' : 'Confirmation undone; history preserved.'
  }
  async changeTab(tab: Tab) {
    await this.flush()
    if (tab === 'compare') await this.loadSessions()
    this.tab = tab
    this.changed()
  }
  async loadSessions() {
    if (!this.state) return
    this.sessions = await this.backend('sessions', {import_id: this.importId, sample_id: this.state.session.sample_id})
  }
  async showHistory() {
    this.history = await this.backend('history', {session_id: this.revision().session_id})
    this.modal = 'history'
  }
  async reviewComponent(signature: string) {
    await this.flush()
    this.setState(await this.backend('review_component', {...this.revision(), signature}), this.work)
    this.notice = 'Conversation review recorded.'
  }
  async validate() {
    await this.flush()
    const state = await this.backend('review_interval', {...this.revision(), checklist: this.checklist})
    this.setState(state, this.work)
    await this.refreshWindows()
    this.notice = 'Interval validated at this revision.'
  }
  async compare(left: string, right: string) {
    this.comparison = await this.backend('compare', {left, right})
  }
  async adjudicate(actor: string, label: string) {
    if (!this.comparison || !this.state) throw new Error('Compare two independent sessions first.')
    const session = await this.backend('open_session', {
      import_id: this.importId, sample_id: this.state.session.sample_id, annotator_id: actor, label,
      kind: 'adjudication', bases: [this.comparison.left.id, this.comparison.right.id],
    })
    this.annotator = actor
    localStorage.setItem('discord.annotator', actor)
    await this.openSession(this.state.session.sample_id, session.id)
  }
  async export() {
    await this.flush()
    this.lastExport = await this.backend('export', this.revision())
    this.notice = 'Results exported to a new local folder.'
  }
  async backup() {
    this.backupPath = (await this.backend('backup', {})).path
    this.notice = 'Consistent database backup created.'
  }
  async saveIdentity(actor: string, pseudonyms: boolean) {
    actor = actor.trim()
    if (!actor || actor.length > 100) throw new Error('Enter an annotator identifier (up to 100 characters).')
    await this.flush()
    if (actor !== this.annotator) {
      this.persistTime()
      this.state = null
      this.work = ''
      this.draft = null
      this.comparison = null
      this.lastExport = null
      localStorage.removeItem('discord.session')
    }
    this.annotator = actor
    this.pseudonyms = pseudonyms
    localStorage.setItem('discord.annotator', actor)
    localStorage.setItem('discord.pseudonyms', String(pseudonyms))
    await this.refreshWindows()
    this.modal = null
  }
  async importSample(path: string, demo = false) {
    if (!demo && !path.trim()) throw new Error('Choose a folder or CSV / Parquet file.')
    await this.flush()
    const {job_id} = demo ? await this.backend('demo', {}) : await this.backend('import', {path: path.trim()})
    while (true) {
      const job = await this.backend('job', {job_id})
      this.importProgress = job.message
      this.changed()
      if (job.status === 'error') throw new Error(job.message)
      if (job.status === 'done') {
        if (!job.result) throw new Error('The import finished without a result.')
        this.imports = await this.backend('imports', {})
        await this.chooseImport(job.result.import_id)
        this.modal = null
        this.importProgress = ''
        this.notice = job.result.reused ? 'Sample already imported. Existing sessions preserved.' : 'Sample imported. Choose an interval.'
        return
      }
      await new Promise(resolve => setTimeout(resolve, 400))
    }
  }
  async switchWorkspace() {
    await this.flush()
    this.persistTime()
    const path = await native<string | null>('pick_path', {kind: 'workspace'})
    if (!path) return
    await native<Config>('switch_workspace', {path})
    this.state = null
    this.draft = null
    this.work = ''
    this.importId = ''
    this.comparison = null
    this.component = ''
    this.lastExport = null
    this.backupPath = ''
    this.tab = 'annotate'
    localStorage.removeItem('discord.session')
    localStorage.removeItem('discord.import')
    this.modal = null
    await this.boot()
    this.notice = 'Workspace opened. Previous data remain in the original folder.'
  }
  async close() {
    if (this.closing) return
    if (this.busy) { this.notice = 'Wait for the current operation before closing.'; this.changed(); return }
    this.closing = true
    this.changed()
    try {
      this.persistTime()
      await this.flush()
      await native('finish_close', {force: false})
    } catch (error) {
      this.closing = false
      this.modal = 'close'
      this.report(error)
    }
  }
  dispose() { clearTimeout(this.timer) }
}
