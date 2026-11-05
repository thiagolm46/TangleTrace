import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {AppModel, eligibleAntecedent, nativeReply} from './model'
import {fixture} from './fixtures.test-support'
import {native} from './transport'
import type {Backend} from './transport'
import type {Protocol} from './types'

vi.mock('./transport', () => ({request: vi.fn(), native: vi.fn()}))
let m: AppModel
const calls: {method: keyof Protocol; params: unknown}[] = []
let handler: (method: keyof Protocol, params: unknown) => unknown
const backend: Backend = async <K extends keyof Protocol>(method: K, params: Protocol[K][0]): Promise<Protocol[K][1]> => {
  calls.push({method, params: structuredClone(params)})
  return await handler(method, params) as Protocol[K][1]
}
beforeEach(() => {
  localStorage.clear()
  calls.length = 0
  handler = method => {
    if (method === 'draft') return {saved: true, updated_at: 'draft-1'}
    if (method === 'windows') return []
    if (method === 'state') return fixture()
    return {saved: true}
  }
  m = new AppModel(backend)
  m.state = fixture()
  m.work = 'P03'
  m.draft = structuredClone(m.state.decisions.P03!)
  m.annotator = 'annotator-a'
})
afterEach(() => { m.dispose(); vi.useRealTimers() })

describe('antecedents and native evidence', () => {
  it('distinguishes visible, outside, self and cross-channel native replies', () => {
    const messages = m.state!.messages
    expect(nativeReply(messages, messages[2]!).eligible).toBe(true)
    expect(nativeReply(messages, messages[4]!).target).toBeUndefined()
    expect(nativeReply(messages, messages[5]!).eligible).toBe(false)
    expect(eligibleAntecedent(messages[2]!, {...messages[0]!, channel_id: 'other'})).toBe(false)
    expect(eligibleAntecedent(messages[2]!, {...messages[0]!, guild_id: 'other'})).toBe(false)
  })
  it('inspection does not annotate and adding changes only the draft', async () => {
    m.inspected = m.state!.messages[2]!
    expect(m.draft!.edges).toHaveLength(0)
    m.addNative(m.inspected)
    m.addNative(m.inspected)
    m.toggleLink('P02')
    expect(m.draft!.edges.map(edge => edge.target_message_id)).toEqual(['P01', 'P02'])
    expect(m.state!.decisions.P03!.edges).toHaveLength(0)
    expect(m.state!.progress.confirmed).toBe(0)
    await m.flush()
    expect(calls.map(call => call.method)).toEqual(['draft'])
  })
  it('rejects later, external and self targets explicitly', () => {
    expect(() => m.toggleLink('P04')).toThrow('earlier')
    m.work = 'P05'
    expect(() => m.addNative(m.state!.messages[4]!)).toThrow('not available')
    m.work = 'P06'
    expect(() => m.addNative(m.state!.messages[5]!)).toThrow('not available')
  })
})

describe('draft safety', () => {
  it('debounces edits at 350ms without confirming', async () => {
    vi.useFakeTimers()
    m.edit(draft => { draft.notes = 'first' })
    await vi.advanceTimersByTimeAsync(200)
    m.edit(draft => { draft.notes = 'second' })
    await vi.advanceTimersByTimeAsync(349)
    expect(calls).toHaveLength(0)
    await vi.advanceTimersByTimeAsync(1)
    expect(calls).toHaveLength(1)
    expect(calls[0]).toMatchObject({method: 'draft', params: {decision: {notes: 'second'}, expected_revision: 0, expected_draft_updated: null}})
  })
  it('serializes in-flight edits and uses the latest draft token', async () => {
    let release: ((value: unknown) => void) | undefined
    let count = 0
    handler = () => ++count === 1 ? new Promise(resolve => { release = resolve }) : {saved: true, updated_at: 'draft-2'}
    m.edit(draft => { draft.notes = 'first' })
    const first = m.flush()
    m.edit(draft => { draft.notes = 'second' })
    release!({saved: true, updated_at: 'draft-1'})
    await first
    expect(calls).toHaveLength(2)
    expect(calls[1]).toMatchObject({params: {decision: {notes: 'second'}, expected_draft_updated: 'draft-1'}})
    expect(m.state!.drafts.P03!.decision.notes).toBe('second')
    expect(m.dirty).toBe(false)
  })
  it('keeps unsaved changes and prevents navigation on save failure', async () => {
    handler = () => { throw new Error('Disk full') }
    m.edit(draft => { draft.notes = 'Do not lose this' })
    await expect(m.selectSource('P04')).rejects.toThrow('Disk full')
    expect(m.work).toBe('P03')
    expect(m.dirty).toBe(true)
    expect(m.saveError).toBe(true)
    expect(m.draft!.notes).toBe('Do not lose this')
    expect(calls.map(call => call.method)).toEqual(['draft'])
  })
  it('makes every concurrent flush wait for the full write queue', async () => {
    const releases: ((value: unknown) => void)[] = []
    handler = method => method === 'draft' ? new Promise(resolve => { releases.push(resolve) }) : {saved: true}
    m.edit(draft => { draft.notes = 'first' })
    const autosave = m.flush()
    m.edit(draft => { draft.notes = 'second' })
    let navigated = false
    const navigation = m.selectSource('P04').then(() => { navigated = true })
    releases[0]!({saved: true, updated_at: 'first-token'})
    await vi.waitFor(() => expect(releases).toHaveLength(2))
    expect(navigated).toBe(false)
    expect(calls.map(call => call.method)).toEqual(['draft', 'draft'])
    releases[1]!({saved: true, updated_at: 'second-token'})
    await Promise.all([autosave, navigation])
    expect(navigated).toBe(true)
    expect(m.state!.drafts.P03!.decision.notes).toBe('second')
  })
  it('saves before navigation and restores the destination draft', async () => {
    m.state!.drafts.P04 = {decision: {...m.state!.decisions.P04!, notes: 'Recovered draft'}, updated_at: 'existing', base_revision: 0}
    m.edit(draft => { draft.notes = 'Save before leaving' })
    await m.selectSource('P04')
    expect(calls.map(call => call.method)).toEqual(['draft', 'cursor'])
    expect(m.work).toBe('P04')
    expect(m.draft!.notes).toBe('Recovered draft')
    expect(m.state!.drafts.P03!.decision.notes).toBe('Save before leaving')
  })
  it('undoes draft edits without mutating confirmed history', async () => {
    m.edit(draft => { draft.notes = 'Edit' })
    await m.undo()
    expect(m.draft!.notes).toBe('')
    await m.undo(true)
    expect(m.draft!.notes).toBe('Edit')
    expect(calls).toHaveLength(0)
  })
  it('discards a draft without touching the confirmed decision', async () => {
    m.edit(draft => { draft.notes = 'Discard' })
    await m.discardDraft()
    expect(calls.map(call => call.method)).toEqual(['discard_draft'])
    expect(m.draft!.notes).toBe('')
    expect(m.dirty).toBe(false)
  })
})

describe('confirmation and lifecycle', () => {
  it('requires an explicit decision', async () => {
    await expect(m.confirm()).rejects.toThrow('Choose a decision')
    expect(calls).toHaveLength(0)
  })
  it('saves then confirms with revision and draft token before advancing', async () => {
    const next = fixture()
    next.decisions.P03 = {...next.decisions.P03!, source_status: 'complete'}
    next.pending = ['P02', 'P04', 'P05', 'P06']
    next.session.graph_revision = 1
    handler = method => method === 'confirm' ? next : method === 'draft' ? {saved: true, updated_at: 'latest'} : method === 'windows' ? [] : {saved: true}
    m.toggleLink('P01')
    await m.confirm()
    expect(calls.map(call => call.method)).toEqual(['draft', 'confirm', 'cursor'])
    expect(calls[1]).toMatchObject({params: {source_id: 'P03', expected_revision: 0, expected_draft_updated: 'latest'}})
    expect(m.work).toBe('P04')
    expect(m.state!.session.graph_revision).toBe(1)
  })
  it('surfaces revision conflicts and does not retry confirmation', async () => {
    m.draft!.source_status = 'no_reply'
    handler = () => { throw new Error('The session changed in another tab.') }
    await m.run(() => m.confirm())
    expect(m.error).toContain('session changed')
    expect(calls.filter(call => call.method === 'confirm')).toHaveLength(1)
    expect(m.state!.session.graph_revision).toBe(0)
    expect(m.busy).toBe(false)
  })
  it('prevents concurrent destructive operations', async () => {
    let release: (() => void) | undefined
    const first = m.run(() => new Promise<void>(resolve => { release = resolve }))
    const other = vi.fn(async () => {})
    await m.run(other)
    expect(other).not.toHaveBeenCalled()
    release!()
    await first
  })
  it('keeps the window open when the final draft save fails', async () => {
    handler = () => { throw new Error('Save failed') }
    m.edit(draft => { draft.notes = 'Pending edit' })
    await m.close()
    expect(m.closing).toBe(false)
    expect(m.modal).toBe('close')
    expect(m.error).toContain('Save failed')
    expect(vi.mocked(native)).not.toHaveBeenCalled()
  })
  it('recovers the saved session and draft from the existing storage keys', async () => {
    const state = fixture()
    state.drafts.P03 = {decision: {...state.decisions.P03!, notes: 'Recovered work'}, updated_at: 'saved-token', base_revision: 0}
    handler = method => {
      if (method === 'config') return {version: '0.3.0', default_source: '', workspace: 'C:\\Synthetic', database: 'C:\\Synthetic\\annotations.sqlite3', exports: 'C:\\Synthetic\\exports'}
      if (method === 'imports') return [{id: 'sample', name: 'Synthetic', source_path: '', provenance: {window_count: 1, target_count: 5, diagnostics: []}}]
      if (method === 'windows') return [state.window]
      if (method === 'state') return state
      throw new Error('Unexpected request')
    }
    localStorage.setItem('discord.annotator', 'annotator-a')
    localStorage.setItem('discord.import', 'sample')
    localStorage.setItem('discord.session', 'session')
    m = new AppModel(backend)
    await m.boot()
    expect(m.work).toBe('P03')
    expect(m.draft!.notes).toBe('Recovered work')
    expect(m.state!.session.graph_revision).toBe(0)
    expect(m.loading).toBe(false)
  })
  it('does not silently hide saved-session load failures', async () => {
    handler = method => {
      if (method === 'config') return {version: '0.3.0', workspace: 'C:\\Synthetic'}
      if (method === 'imports' || method === 'windows') return []
      throw new Error('Saved session unavailable')
    }
    localStorage.setItem('discord.session', 'missing')
    await m.run(() => m.boot())
    expect(m.error).toBe('Saved session unavailable')
    expect(localStorage.getItem('discord.session')).toBe('missing')
    expect(m.loading).toBe(false)
  })
  it('exports the confirmed snapshot with the exact current revision', async () => {
    m.state!.session.graph_revision = 7
    handler = method => method === 'export' ? {directory: 'C:\\Synthetic\\exports\\one', manifest: {status: 'in_progress'}} : {saved: true}
    await m.export()
    expect(calls[0]).toEqual({method: 'export', params: {session_id: 'session', expected_revision: 7}})
    expect(m.lastExport).toMatchObject({manifest: {status: 'in_progress'}})
  })
})
