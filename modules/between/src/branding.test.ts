import {readFileSync} from 'node:fs'
import {expect, it} from 'vitest'

it('keeps the BETWEEN package names and lock files consistent', () => {
  const project: {name: string} = JSON.parse(readFileSync('package.json', 'utf8'))
  const lock: {name: string, packages: Record<string, {name: string}>} =
    JSON.parse(readFileSync('package-lock.json', 'utf8'))
  expect(project.name).toBe('tangletrace-between')
  expect(lock.name).toBe(project.name)
  expect(lock.packages['']?.name).toBe(project.name)
  expect(readFileSync('pyproject.toml', 'utf8')).toContain('name = "tangletrace-between"')
  expect(readFileSync('src-tauri/Cargo.toml', 'utf8')).toContain('name = "tangletrace-between"')
  expect(readFileSync('src-tauri/Cargo.lock', 'utf8')).toContain('name = "tangletrace-between"')
})

it('brands the native window without changing the existing workspace identifier', () => {
  const config: {productName: string, identifier: string, app: {windows: {title: string}[]}} =
    JSON.parse(readFileSync('src-tauri/tauri.conf.json', 'utf8'))
  expect(config.productName).toBe('TangleTrace BETWEEN')
  expect(config.app.windows[0]?.title).toBe('TangleTrace BETWEEN - Reply-Link Annotation & Review')
  expect(config.identifier).toBe('br.edu.discord-se.annotator')
})

it('uses the renamed executable in launch and distribution scripts', () => {
  expect(readFileSync('Start-Desktop.ps1', 'utf8')).toContain('src-tauri\\target\\debug\\tangletrace-between.exe')
  expect(readFileSync('Build-Desktop.ps1', 'utf8')).toContain('src-tauri\\target\\release\\tangletrace-between.exe')
})
