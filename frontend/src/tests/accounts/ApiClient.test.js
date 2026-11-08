import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client.js'
import { changeNickname, login, readSession } from '../../api/accounts.js'

afterEach(() => vi.unstubAllGlobals())

test('writes include cookie credentials and CSRF and only send the current account nickname', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ id: 1, nickname: '학습자' }) })
  vi.stubGlobal('fetch', fetchMock)
  const csrf = crypto.randomUUID()
  await changeNickname('학습자', csrf)
  const [url, options] = fetchMock.mock.calls[0]
  expect(url).toBe('http://localhost:8000/api/accounts/me')
  expect(options.credentials).toBe('include')
  expect(options.headers['X-CSRF-Token']).toBe(csrf)
  expect(JSON.parse(options.body)).toEqual({ nickname: '학습자' })
})

test('API errors preserve status for session recovery', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, json: async () => ({ detail: '로그인이 필요합니다.' }) }))
  await expect(login({ email: 'one@example.com', password: crypto.randomUUID() }, crypto.randomUUID()))
    .rejects.toMatchObject({ status: 401, message: '로그인이 필요합니다.' })
})

test('network failure becomes a safe connection message', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')))
  await expect(readSession()).rejects.toBeInstanceOf(ApiError)
})

test('simultaneous session bootstrap calls share one cookie-setting request', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ user: null, csrf_token: crypto.randomUUID() }) })
  vi.stubGlobal('fetch', fetchMock)
  const [first, second] = await Promise.all([readSession(), readSession()])
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(first).toBe(second)
})
