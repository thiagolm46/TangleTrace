import {afterEach, beforeAll, beforeEach, expect, it, vi} from 'vitest'
import {act, cleanup, fireEvent, render, screen} from '@testing-library/react'
import {BaseStyles, ThemeProvider} from '@primer/react'
import {Annotation, MessageCard} from './Annotation'
import {App} from './App'
import {Dialogs} from './Dialogs'
import {AppModel} from './model'
import {fixture} from './fixtures.test-support'

vi.mock('./transport', () => ({request: vi.fn(async () => ({saved: true, updated_at: 'draft'})), native: vi.fn()}))
vi.mock('@tauri-apps/api/event', () => ({listen: vi.fn(async () => vi.fn())}))
beforeAll(() => {
  Object.defineProperty(Document.prototype, 'adoptedStyleSheets', {value: [], writable: true, configurable: true})
  Object.defineProperty(ShadowRoot.prototype, 'adoptedStyleSheets', {value: [], writable: true, configurable: true})
  window.matchMedia = vi.fn().mockImplementation(query => ({matches: false, media: query, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {}}))
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} }
  HTMLElement.prototype.scrollIntoView = vi.fn()
})
let m: AppModel
beforeEach(() => {
  localStorage.clear()
  m = new AppModel()
  m.state = fixture()
  m.work = 'P03'
  m.draft = structuredClone(m.state.decisions.P03!)
})
afterEach(() => { cleanup(); m.dispose() })
function mount(content: React.ReactNode) {
  return render(<ThemeProvider><BaseStyles>{content}</BaseStyles></ThemeProvider>)
}
it('shows the BETWEEN identity in the application header', () => {
  vi.spyOn(m, 'boot').mockResolvedValue()
  mount(<App model={m} />)
  expect(screen.getByRole('heading', {name: 'TangleTrace BETWEEN', level: 1})).toBeDefined()
  expect(screen.getByText('Reply-Link Annotation & Review')).toBeDefined()
})
it('renders corpus content as text, never executable HTML', () => {
  const {container} = mount(<MessageCard model={m} message={m.state!.messages[0]!} />)
  expect(container.querySelector('img')).toBeNull()
  expect(screen.getByText(/<img src=x/)).toBeDefined()
})
it('uses English labels and shows native evidence separately', () => {
  mount(<Annotation model={m} />)
  expect(screen.getByText('Target 2 of 5')).toBeDefined()
  expect(screen.getByText('Native Discord reply evidence')).toBeDefined()
  expect(screen.getByLabelText('Decision')).toBeDefined()
  expect(screen.getByRole('button', {name: 'Confirm decision and advance'}).hasAttribute('disabled')).toBe(true)
  fireEvent.click(screen.getByRole('button', {name: 'Add as antecedent'}))
  expect(m.draft!.edges).toHaveLength(1)
  expect(m.state!.decisions.P03!.edges).toHaveLength(0)
})
it('Enter on a button does not invoke the global confirm shortcut', () => {
  const confirm = vi.spyOn(m, 'confirm')
  mount(<Annotation model={m} />)
  fireEvent.keyDown(screen.getByRole('button', {name: 'Inspect reply'}), {key: 'Enter'})
  expect(confirm).not.toHaveBeenCalled()
})
it('Enter on the stream invokes confirmation once', async () => {
  const confirm = vi.spyOn(m, 'confirm').mockResolvedValue()
  mount(<Annotation model={m} />)
  await act(async () => { fireEvent.keyDown(document.body, {key: 'Enter'}) })
  expect(confirm).toHaveBeenCalledTimes(1)
})
it('uses a Primer dialog for the guide with English close control', () => {
  m.modal = 'guide'
  mount(<Dialogs model={m} />)
  expect(screen.getByRole('dialog')).toBeDefined()
  expect(screen.getByRole('button', {name: 'Close'})).toBeDefined()
  expect(screen.getByText('Keyboard shortcuts')).toBeDefined()
})
