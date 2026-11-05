import {invoke} from '@tauri-apps/api/core'
import type {Protocol} from './types'

export async function native<T>(command: string, args: Record<string, unknown> = {}): Promise<T> {
  try {
    return await invoke<T>(command, args)
  } catch (error) {
    throw new Error(typeof error === 'string' ? error : error instanceof Error ? error.message : 'The local operation failed.')
  }
}

export type Backend = <K extends keyof Protocol>(method: K, params: Protocol[K][0]) => Promise<Protocol[K][1]>
export const request: Backend = (method, params) => native('backend_request', {method, params})
