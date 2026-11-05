import {beforeEach, expect, it, vi} from 'vitest'
import {invoke} from '@tauri-apps/api/core'
import {native, request} from './transport'

vi.mock('@tauri-apps/api/core', () => ({invoke: vi.fn()}))
beforeEach(() => { vi.mocked(invoke).mockReset() })
it('sends the existing backend_request command with unchanged protocol parameters', async () => {
  vi.mocked(invoke).mockResolvedValue({session: {id: 'session'}})
  await request('state', {session_id: 'session'})
  expect(invoke).toHaveBeenCalledWith('backend_request', {method: 'state', params: {session_id: 'session'}})
})
it('surfaces Rust string errors as explicit JavaScript errors', async () => {
  vi.mocked(invoke).mockRejectedValue('Workspace is locked')
  await expect(native('switch_workspace', {path: 'C:\\Synthetic'})).rejects.toThrow('Workspace is locked')
})
it('preserves JavaScript error messages without a success-shaped fallback', async () => {
  vi.mocked(invoke).mockRejectedValue(new Error('IPC unavailable'))
  await expect(request('imports', {})).rejects.toThrow('IPC unavailable')
})
