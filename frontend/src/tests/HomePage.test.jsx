import { afterEach, expect, test, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import HomePage from '../pages/HomePage.jsx'

function App() {
  return <MemoryRouter><HomePage /></MemoryRouter>
}

vi.mock('../auth/AuthContext.jsx', () => ({ useAuth: () => ({ user: { nickname: '학습자' } }) }))

afterEach(() => vi.unstubAllGlobals())

test('shows successful connection after calling the API with credentials', async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true, json: async () => ({ status: 'ok', service: 'BuildLog' }),
  })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  expect(screen.getByRole('status').textContent).toContain('연결 확인 중')
  await screen.findByText('서비스 연결 완료')
  expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/health', expect.objectContaining({ credentials: 'include' }))
})

test('allows retrying a failed connection', async () => {
  const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError('offline'))
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'ok', service: 'BuildLog' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: '다시 확인' }))
  await screen.findByText('서비스 연결 완료')
  expect(fetchMock).toHaveBeenCalledTimes(2)
})

test('does not report success for an HTTP failure or unexpected payload', async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({ ok: false })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'unknown' }) })
  vi.stubGlobal('fetch', fetchMock)
  render(<App />)
  fireEvent.click(await screen.findByRole('button', { name: '다시 확인' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
  await screen.findByText('서비스에 연결할 수 없어요')
  expect(screen.queryByText('서비스 연결 완료')).toBeNull()
})
