import { beforeEach, afterEach, expect, test, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../App.jsx'
import * as accounts from '../api/accounts.js'
import * as materials from '../api/materials.js'
import { mergeAnalysis } from '../pages/materials/useMaterialAnalysis.js'

vi.mock('../api/materials.js', () => ({ getMaterials: vi.fn(), uploadMaterial: vi.fn(), deleteMaterial: vi.fn(), getOriginal: vi.fn(), getMaterialAnalysis: vi.fn(), retryMaterialAnalysis: vi.fn() }))
vi.mock('../api/accounts.js', () => ({ readSession: vi.fn(), signup: vi.fn(), login: vi.fn(), changeNickname: vi.fn() }))
const analysis = (status, version = 1, extra = {}) => ({ status, version, summary: null, error_code: null, error_message: null, scope: null, completed_at: null, attempt_count: 0, can_retry: false, ...extra })
const item = { id: 1, title: '화면 학습', memo: null, original_filename: 'notes.png', media_type: 'image', mime_type: 'image/png', size_bytes: 5, created_at: '2026-10-24T00:00:00Z' }

beforeEach(() => {
  vi.resetAllMocks()
  accounts.readSession.mockResolvedValue({ user: { id: 1, nickname: '학습자' }, csrf_token: 'test-csrf' })
  vi.stubGlobal('confirm', vi.fn(() => true))
  vi.stubGlobal('fetch', vi.fn(() => { throw Error('No network in unit tests') }))
})
afterEach(() => vi.unstubAllGlobals())

async function open(state) {
  materials.getMaterials.mockResolvedValue([{ ...item, analysis: state }])
  const page = render(<MemoryRouter initialEntries={['/materials']}><AppRoutes /></MemoryRouter>)
  await screen.findByRole('heading', { name: '화면 학습' })
  return page
}

test('polls a pending job and renders the summary as plain text without extra mutations', async () => {
  materials.getMaterialAnalysis.mockResolvedValue(analysis('succeeded', 3, { summary: '<script>학습 요약</script>', scope: { kind: 'video_frames', frame_count: 3 } }))
  await open(analysis('pending'))
  expect(await screen.findByText('<script>학습 요약</script>')).toBeTruthy()
  expect(document.querySelector('script')).toBeNull()
  expect(screen.getByText('영상 화면 3장 기준 · 음성 미포함')).toBeTruthy()
  expect(materials.getMaterialAnalysis).toHaveBeenCalledTimes(1)
  expect(materials.retryMaterialAnalysis).not.toHaveBeenCalled()
})

test('keeps original/delete usable during analysis and aborts polling on unmount', async () => {
  materials.getMaterialAnalysis.mockImplementation(() => new Promise(() => {}))
  const page = await open(analysis('processing', 2))
  await waitFor(() => expect(materials.getMaterialAnalysis).toHaveBeenCalledTimes(1))
  expect(screen.getByRole('button', { name: '원본 보기' }).disabled).toBe(false)
  expect(screen.getByRole('button', { name: '삭제' }).disabled).toBe(false)
  const signal = materials.getMaterialAnalysis.mock.calls[0][1]
  page.unmount()
  expect(signal.aborted).toBe(true)
})

test('only retries after confirmation using the existing CSRF session', async () => {
  materials.retryMaterialAnalysis.mockResolvedValue(analysis('pending', 4))
  materials.getMaterialAnalysis.mockResolvedValue(analysis('succeeded', 6, { summary: '재시도한 요약입니다.' }))
  await open(analysis('failed', 3, { error_message: '원본은 유지돼요.', can_retry: true, attempt_count: 1 }))
  expect(screen.getByText('원본은 유지돼요.')).toBeTruthy()
  confirm.mockReturnValueOnce(false)
  fireEvent.click(screen.getByRole('button', { name: '다시 요약' }))
  expect(materials.retryMaterialAnalysis).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '다시 요약' }))
  expect(await screen.findByText('재시도한 요약입니다.')).toBeTruthy()
  expect(materials.retryMaterialAnalysis.mock.calls[0].slice(0, 2)).toEqual([1, 'test-csrf'])
})

test('never requests analysis for old records or succeeded records', async () => {
  await open(analysis('not_requested', 0))
  expect(screen.getByText('기존 자료는 자동 분석하지 않아요.')).toBeTruthy()
  expect(materials.getMaterialAnalysis).not.toHaveBeenCalled()
  expect(screen.queryByRole('button', { name: '다시 요약' })).toBeNull()
})

test('does not overwrite newer versions or recreate a deleted item', () => {
  const original = [{ ...item, analysis: analysis('succeeded', 5, { summary: '최신 요약' }) }]
  expect(mergeAnalysis(original, 1, analysis('pending', 1))).toEqual(original)
  expect(mergeAnalysis([], 1, analysis('succeeded', 6))).toEqual([])
})

test('limits polling to two concurrent requests and cancels filtered requests', async () => {
  materials.getMaterials.mockResolvedValue([1, 2, 3].map(id => ({ ...item, id, title: `자료 ${id}`, analysis: analysis('pending') })))
  materials.getMaterialAnalysis.mockImplementation(() => new Promise(() => {}))
  const page = render(<MemoryRouter initialEntries={['/materials']}><AppRoutes /></MemoryRouter>)
  await screen.findByRole('heading', { name: '자료 3' })
  await waitFor(() => expect(materials.getMaterialAnalysis).toHaveBeenCalledTimes(2))
  const signals = materials.getMaterialAnalysis.mock.calls.map(call => call[1])
  fireEvent.click(screen.getByRole('button', { name: '영상 0' }))
  expect(signals.every(signal => signal.aborted)).toBe(true)
  expect(materials.getMaterialAnalysis).toHaveBeenCalledTimes(2)
  page.unmount()
})
