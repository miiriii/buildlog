import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { getMaterials, uploadMaterial, deleteMaterial, getOriginal } from '../api/materials.js'

const item = { id: 1, title: '공부', memo: null, original_filename: 'a.png', media_type: 'image', mime_type: 'image/png', size_bytes: 5, created_at: '2026-10-24T00:00:00Z' }
const response = (data, status = 200) => ({ ok: status < 400, status, json: vi.fn().mockResolvedValue(data) })
beforeEach(() => vi.stubGlobal('fetch', vi.fn()))
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers() })

test('uploads FormData with cookies and CSRF without setting Content-Type', async () => {
  fetch.mockResolvedValue(response(item, 201))
  const token = crypto.randomUUID()
  await uploadMaterial({ title: '공부', memo: '메모', file: new File(['image'], 'a.png', { type: 'image/png' }) }, token)
  const [url, options] = fetch.mock.calls[0]
  expect(url).toBe('http://localhost:8000/api/materials')
  expect(options.credentials).toBe('include')
  expect(options.headers['Content-Type']).toBeUndefined()
  expect(options.headers['X-CSRF-Token']).toBe(token)
  expect(options.body).toBeInstanceOf(FormData)
  expect(options.body.get('file').name).toBe('a.png')
  expect(options.body.get('memo')).toBe('메모')
})

test('accepts 204 without reading JSON', async () => {
  const empty = response(null, 204)
  fetch.mockResolvedValue(empty)
  await deleteMaterial(1, crypto.randomUUID())
  expect(empty.json).not.toHaveBeenCalled()
  expect(fetch.mock.calls[0][1].method).toBe('DELETE')
})

test('checks list response and original MIME and byte count', async () => {
  fetch.mockResolvedValueOnce(response({ items: [item] })).mockResolvedValueOnce(response({ wrong: [] }))
  expect(await getMaterials()).toEqual([item])
  await expect(getMaterials()).rejects.toThrow('자료 목록 응답')
  fetch.mockResolvedValueOnce({ ok: true, status: 200, blob: async () => new Blob(['image'], { type: 'image/png' }) })
  expect((await getOriginal(item)).size).toBe(5)
  fetch.mockResolvedValueOnce({ ok: true, status: 200, blob: async () => new Blob(['wrong'], { type: 'text/html' }) })
  await expect(getOriginal(item)).rejects.toThrow('원본 파일 응답')
})

test('preserves HTTP error status and never retries writes', async () => {
  fetch.mockResolvedValue(response({ detail: '등록할 수 없습니다.' }, 415))
  await expect(uploadMaterial({ title: '공부', file: new File(['x'], 'a.png') }, crypto.randomUUID())).rejects.toMatchObject({ status: 415, message: '등록할 수 없습니다.' })
  expect(fetch).toHaveBeenCalledTimes(1)
})

test('upload timeout aborts once and reports uncertain outcome without retrying', async () => {
  vi.useFakeTimers()
  fetch.mockImplementation((_, { signal }) => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('abort', 'AbortError')))))
  const pending = uploadMaterial({ title: '공부', file: new File(['x'], 'a.png') }, crypto.randomUUID())
  const check = expect(pending).rejects.toThrow('목록을 새로 확인')
  await vi.advanceTimersByTimeAsync(180000)
  await check
  expect(fetch).toHaveBeenCalledTimes(1)
})
