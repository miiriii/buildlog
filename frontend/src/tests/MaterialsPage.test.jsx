import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { act, fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AppRoutes } from '../App.jsx'
import * as accounts from '../api/accounts.js'
import * as materials from '../api/materials.js'
import { ApiError } from '../api/client.js'

vi.mock('../api/materials.js', () => ({ getMaterials: vi.fn(), uploadMaterial: vi.fn(), deleteMaterial: vi.fn(), getOriginal: vi.fn(), getMaterialAnalysis: vi.fn(), retryMaterialAnalysis: vi.fn() }))

const samples = [
  { id: 3, title: 'REST API 핵심 정리', original_filename: 'rest-api-notes.png', media_type: 'image', mime_type: 'image/png', size_bytes: 5, memo: '캡처 메모', created_at: '2026-10-20T00:00:00Z' },
  { id: 2, title: '회원가입 동작 확인', original_filename: 'signup-demo.mp4', media_type: 'video', mime_type: 'video/mp4', size_bytes: 5, memo: null, created_at: '2026-10-19T00:00:00Z' },
  { id: 1, title: '데이터베이스 관계 정리', original_filename: 'database-schema.jpg', media_type: 'image', mime_type: 'image/jpeg', size_bytes: 5, memo: null, created_at: '2026-10-18T00:00:00Z' },
]

vi.mock('../api/accounts.js', () => ({
  readSession: vi.fn(), signup: vi.fn(), login: vi.fn(), changeNickname: vi.fn(),
}))

beforeEach(() => {
  vi.resetAllMocks()
  accounts.readSession.mockResolvedValue({ user: { id: 1, nickname: '학습자' }, csrf_token: crypto.randomUUID() })
  materials.getMaterials.mockResolvedValue(samples)
  vi.stubGlobal('confirm', vi.fn().mockReturnValue(true))
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn().mockReturnValue('blob:test'), revokeObjectURL: vi.fn() }))
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network request') }))
})
afterEach(() => vi.unstubAllGlobals())

async function openMaterials() {
  const page = render(<MemoryRouter initialEntries={['/materials']}><AppRoutes /></MemoryRouter>)
  await screen.findByRole('heading', { name: '학습 자료함' })
  await waitFor(() => expect(screen.getByRole('button', { name: '목록 새로 확인' }).disabled).toBe(false))
  return page
}

test('filters example cards by type without uploading or changing the list', async () => {
  await openMaterials()
  const list = screen.getByRole('list', { name: '내 자료 목록' })
  expect(within(list).getAllByRole('listitem')).toHaveLength(3)
  fireEvent.click(screen.getByRole('button', { name: '이미지 2' }))
  expect(within(list).getAllByRole('listitem')).toHaveLength(2)
  expect(within(list).queryByText('회원가입 동작 확인')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '영상 1' }))
  expect(within(list).getAllByRole('listitem')).toHaveLength(1)
  expect(within(list).getByText('signup-demo.mp4')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '전체 3' }))
  expect(within(list).getAllByRole('listitem')).toHaveLength(3)
  expect(fetch).not.toHaveBeenCalled()
})

test('allows draft typing and picking and requires a file before uploading', async () => {
  await openMaterials()
  const title = screen.getByLabelText('자료 제목')
  const memo = screen.getByLabelText('메모 · 선택')
  fireEvent.change(title, { target: { value: '나의 자료' } })
  fireEvent.change(memo, { target: { value: '복습 메모' } })
  expect(title.value).toBe('나의 자료')
  expect(memo.value).toBe('복습 메모')
  expect(screen.getByRole('button', { name: '파일 선택' }).disabled).toBe(false)
  for (const name of ['자료 업로드']) {
    for (const button of screen.getAllByRole('button', { name })) expect(button.disabled).toBe(true)
  }
  fireEvent.submit(title.closest('form'))
  expect(screen.getByText('나만 볼 수 있는 비공개 자료입니다.')).toBeTruthy()
  expect(screen.queryByText(/디자인 확인용 예시/)).toBeNull()
  expect(materials.uploadMaterial).not.toHaveBeenCalled()
  expect(screen.getByText('PNG · JPG(JPEG) 최대 5MiB / MP4 최대 30MiB')).toBeTruthy()
  expect(fetch).not.toHaveBeenCalled()
})

test('selects, replaces, cancels and reselects files without sending requests or changing examples', async () => {
  await openMaterials()
  const input = screen.getByLabelText('자료 파일')
  const picker = vi.spyOn(input, 'click')
  fireEvent.click(screen.getByRole('button', { name: '파일 선택' }))
  expect(picker).toHaveBeenCalledTimes(1)
  const file = new File(['image'], '나의 캡처.PNG', { type: 'image/png' })
  fireEvent.change(input, { target: { files: [file] } })
  expect(screen.getByRole('status').textContent).toContain('나의 캡처.PNG')
  expect(screen.getByRole('status').textContent).toContain('5바이트')
  fireEvent.change(input, { target: { files: [] } })
  expect(screen.getByRole('status').textContent).toContain('나의 캡처.PNG')
  const video = new File(['video'], '실습.mp4', { type: 'video/mp4' })
  fireEvent.change(input, { target: { files: [video] } })
  expect(screen.getByRole('status').textContent).toContain('MP4 영상')
  fireEvent.change(input, { target: { files: [video] } })
  expect(screen.getByRole('status').textContent).toContain('실습.mp4')
  fireEvent.change(input, { target: { files: [new File(['x'], 'invalid.txt')] } })
  expect(screen.queryByRole('status')).toBeNull()
  expect(screen.getByRole('alert').textContent).toContain('PNG·JPG')
  fireEvent.change(input, { target: { files: [file] } })
  expect(screen.queryByRole('alert')).toBeNull()
  expect(screen.getByRole('status').textContent).toContain('아직 저장되지 않았어요')
  expect(within(screen.getByRole('list', { name: '내 자료 목록' })).getAllByRole('listitem')).toHaveLength(3)
  expect(fetch).not.toHaveBeenCalled()
})

test('shows input errors, counts Unicode characters, and trims only title edges on blur', async () => {
  await openMaterials()
  const title = screen.getByLabelText('자료 제목')
  const memo = screen.getByLabelText('메모 · 선택')
  fireEvent.blur(title)
  expect(title.getAttribute('aria-invalid')).toBe('true')
  fireEvent.change(title, { target: { value: '  오늘  공부  ' } })
  fireEvent.blur(title)
  expect(title.value).toBe('오늘  공부')
  expect(title.getAttribute('aria-invalid')).toBe('false')
  fireEvent.change(title, { target: { value: '😀'.repeat(100) } })
  expect(title.getAttribute('aria-invalid')).toBe('false')
  fireEvent.change(title, { target: { value: '가'.repeat(101) } })
  expect(title.getAttribute('aria-invalid')).toBe('true')
  fireEvent.change(memo, { target: { value: '😀'.repeat(1000) } })
  expect(memo.getAttribute('aria-invalid')).toBe('false')
  fireEvent.change(memo, { target: { value: '가'.repeat(1001) } })
  expect(memo.getAttribute('aria-invalid')).toBe('true')
  expect(fetch).not.toHaveBeenCalled()
})

test('uses existing login protection for direct access', async () => {
  accounts.readSession.mockResolvedValue({ user: null, csrf_token: crypto.randomUUID() })
  render(<MemoryRouter initialEntries={['/materials']}><AppRoutes /></MemoryRouter>)
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.queryByRole('heading', { name: '학습 자료함' })).toBeNull()
})

test('existing home menu opens materials through React Router', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) }))
  render(<MemoryRouter initialEntries={['/']}><AppRoutes /></MemoryRouter>)
  fireEvent.click(await screen.findByRole('link', { name: '학습 자료함' }))
  await screen.findByRole('heading', { name: '학습 자료함' })
  expect(screen.getByRole('link', { name: '대시보드' }).getAttribute('href')).toBe('/dashboard')
})

function fillDraft() {
  fireEvent.change(screen.getByLabelText('자료 제목'), { target: { value: '  새로운  공부  ' } })
  fireEvent.change(screen.getByLabelText('메모 · 선택'), { target: { value: '나의 메모' } })
  fireEvent.change(screen.getByLabelText('자료 파일'), { target: { files: [new File(['image'], 'new.png', { type: 'image/png' })] } })
}

test('only clears inputs and adds a card after upload success; prevents duplicate submissions', async () => {
  let finish
  materials.uploadMaterial.mockReturnValue(new Promise(resolve => { finish = resolve }))
  await openMaterials()
  fillDraft()
  const form = screen.getByLabelText('자료 제목').closest('form')
  fireEvent.submit(form); fireEvent.submit(form)
  expect(materials.uploadMaterial).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('자료 제목').value).toContain('새로운')
  expect(screen.queryByText('자료를 저장했어요.')).toBeNull()
  expect(screen.getByLabelText('자료 제목').disabled).toBe(true)
  await act(async () => finish({ ...samples[0], id: 4, title: '새로운  공부', original_filename: 'new.png' }))
  await screen.findByText('자료를 저장했어요.')
  expect(screen.getByLabelText('자료 제목').value).toBe('')
  expect(screen.getByLabelText('메모 · 선택').value).toBe('')
  expect(screen.getByRole('button', { name: '전체 4' })).toBeTruthy()
  expect(materials.uploadMaterial.mock.calls[0][0].title).toBe('새로운  공부')
})

test.each([413, 415, 422, 503, 0])('upload failure %s preserves draft and files without replaying', async status => {
  materials.uploadMaterial.mockRejectedValue(new ApiError('저장 실패 안내', status))
  await openMaterials(); fillDraft()
  fireEvent.click(screen.getByRole('button', { name: '자료 업로드' }))
  await screen.findByText('저장 실패 안내')
  expect(screen.getByLabelText('자료 제목').value).toContain('새로운')
  expect(screen.getByLabelText('메모 · 선택').value).toBe('나의 메모')
  expect(screen.getByText('new.png')).toBeTruthy()
  expect(materials.uploadMaterial).toHaveBeenCalledTimes(1)
  expect(screen.getByRole('button', { name: '전체 3' })).toBeTruthy()
  expect(screen.queryByText('자료를 저장했어요.')).toBeNull()
})

test('CSRF failure refreshes existing session but never retries upload automatically', async () => {
  materials.uploadMaterial.mockRejectedValue(new ApiError('요청 확인 만료', 403))
  await openMaterials(); fillDraft()
  fireEvent.click(screen.getByRole('button', { name: '자료 업로드' }))
  await screen.findByText('요청 확인 만료')
  expect(accounts.readSession).toHaveBeenCalledTimes(2)
  expect(materials.uploadMaterial).toHaveBeenCalledTimes(1)
  expect(screen.getByText('new.png')).toBeTruthy()
})

test('expired session on list refresh follows existing login protection', async () => {
  await openMaterials()
  accounts.readSession.mockResolvedValue({ user: null, csrf_token: crypto.randomUUID() })
  materials.getMaterials.mockRejectedValue(new ApiError('로그인이 필요합니다.', 401))
  fireEvent.click(screen.getByRole('button', { name: '목록 새로 확인' }))
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.queryByRole('list', { name: '내 자료 목록' })).toBeNull()
})

test('distinguishes list failure, retry, empty list and filter empty state', async () => {
  materials.getMaterials.mockRejectedValueOnce(new ApiError('목록 연결 실패', 503)).mockResolvedValueOnce([])
  render(<MemoryRouter initialEntries={['/materials']}><AppRoutes /></MemoryRouter>)
  await screen.findByText('목록 연결 실패')
  expect(screen.queryByText(/아직 등록한 자료가/)).toBeNull()
  expect(screen.queryByText('REST API 핵심 정리')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '다시 불러오기' }))
  await screen.findByText(/아직 등록한 자료가/)
  materials.getMaterials.mockResolvedValue([samples[0]])
  fireEvent.click(screen.getByRole('button', { name: '목록 새로 확인' }))
  fireEvent.click(await screen.findByRole('button', { name: '이미지 1' }))
  fireEvent.click(screen.getByRole('button', { name: '영상 0' }))
  expect(screen.getByText('이 종류의 자료가 없어요.')).toBeTruthy()
})

test('delete confirmation, failure and successful 204 update cards correctly', async () => {
  await openMaterials()
  const first = () => within(screen.getByRole('list', { name: '내 자료 목록' })).getAllByRole('listitem')[0]
  confirm.mockReturnValueOnce(false)
  fireEvent.click(within(first()).getByRole('button', { name: '삭제' }))
  expect(materials.deleteMaterial).not.toHaveBeenCalled()
  materials.deleteMaterial.mockRejectedValueOnce(new ApiError('삭제 실패', 503)).mockResolvedValueOnce(undefined)
  fireEvent.click(within(first()).getByRole('button', { name: '삭제' }))
  await screen.findByText('삭제 실패')
  expect(screen.getByRole('button', { name: '전체 3' })).toBeTruthy()
  fireEvent.click(within(first()).getByRole('button', { name: '삭제' }))
  await screen.findByText('자료를 삭제했어요.')
  expect(screen.getByRole('button', { name: '전체 2' })).toBeTruthy()
})

test('delete 404 rechecks server state without pretending success', async () => {
  await openMaterials()
  materials.deleteMaterial.mockRejectedValue(new ApiError('없음', 404))
  materials.getMaterials.mockResolvedValue(samples.slice(1))
  fireEvent.click(screen.getAllByRole('button', { name: '삭제' })[0])
  await screen.findByText(/자료가 없거나 접근할 수 없습니다/)
  await screen.findByRole('button', { name: '전체 2' })
  expect(materials.deleteMaterial).toHaveBeenCalledTimes(1)
  expect(screen.queryByText('자료를 삭제했어요.')).toBeNull()
})

test('original view shows a Blob image and releases URL on close and unmount', async () => {
  materials.getOriginal.mockResolvedValue(new Blob(['image'], { type: 'image/png' }))
  const page = await openMaterials()
  fireEvent.click(screen.getAllByRole('button', { name: '원본 보기' })[0])
  expect((await screen.findByRole('img', { name: samples[0].title })).getAttribute('src')).toBe('blob:test')
  fireEvent.click(screen.getByRole('button', { name: '원본 닫기' }))
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:test')
  fireEvent.click(screen.getAllByRole('button', { name: '원본 보기' })[0])
  await screen.findByRole('img', { name: samples[0].title })
  page.unmount()
  expect(URL.revokeObjectURL).toHaveBeenCalledTimes(2)
})

test('unmount aborts pending upload and remount fetches saved state rather than keeping a draft', async () => {
  let signal
  materials.uploadMaterial.mockImplementation((_, token, requestSignal) => { signal = requestSignal; return new Promise(() => {}) })
  const page = await openMaterials(); fillDraft()
  fireEvent.click(screen.getByRole('button', { name: '자료 업로드' }))
  page.unmount()
  expect(signal.aborted).toBe(true)
  await openMaterials()
  expect(screen.getByLabelText('자료 제목').value).toBe('')
  expect(screen.queryByText('new.png')).toBeNull()
  expect(materials.getMaterials).toHaveBeenCalledTimes(2)
})
