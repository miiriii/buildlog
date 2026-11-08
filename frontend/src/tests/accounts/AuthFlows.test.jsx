import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { AppRoutes } from '../../App.jsx'
import * as accounts from '../../api/accounts.js'

vi.mock('../../api/accounts.js', () => ({
  readSession: vi.fn(), signup: vi.fn(), login: vi.fn(), changeNickname: vi.fn(),
}))

const user = { id: 1, email: 'one@example.com', nickname: '학습자' }
const anonymous = () => ({ user: null, csrf_token: crypto.randomUUID() })
const signedIn = () => ({ user, csrf_token: crypto.randomUUID() })

function Location() {
  const location = useLocation()
  return <span data-testid="route">{location.pathname}</span>
}

function open(path) {
  render(<MemoryRouter initialEntries={[path]}><AppRoutes /><Location /></MemoryRouter>)
}

function type(label, value) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } })
}

beforeEach(() => {
  vi.resetAllMocks()
  accounts.readSession.mockResolvedValue(anonymous())
  accounts.signup.mockResolvedValue({ message: '회원가입 완료' })
  accounts.login.mockResolvedValue(signedIn())
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok', service: 'BuildLog' }) }))
})
afterEach(() => vi.unstubAllGlobals())

test.each(['/', '/settings', '/dashboard', '/records/studies', '/records/public'])('anonymous direct access to %s goes to login', async path => {
  open(path)
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.getByTestId('route').textContent).toBe('/login')
  expect(screen.queryByText('현재 닉네임:')).toBeNull()
})

test('signup success moves to login without automatically signing in', async () => {
  open('/signup')
  await screen.findByRole('heading', { name: '회원가입' })
  type('이메일', ' one@example.com ')
  type('닉네임', ' 학습자 ')
  type('비밀번호', crypto.randomUUID())
  fireEvent.click(screen.getByRole('button', { name: '회원가입' }))
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.getByTestId('route').textContent).toBe('/login')
  expect(screen.getByRole('status').textContent).toContain('회원가입을 마쳤어요')
  expect(screen.getByLabelText('비밀번호').value).toBe('')
  expect(accounts.signup.mock.calls[0][0]).toMatchObject({ email: 'one@example.com', nickname: '학습자' })
})

test.each([409, 422, 503])('signup failure %s keeps email and nickname and clears only password', async status => {
  accounts.signup.mockRejectedValue(Object.assign(new Error('가입 정보를 확인해 주세요.'), { status }))
  open('/signup')
  await screen.findByRole('heading', { name: '회원가입' })
  type('이메일', 'one@example.com')
  type('닉네임', '학습자')
  type('비밀번호', crypto.randomUUID())
  fireEvent.click(screen.getByRole('button', { name: '회원가입' }))
  await screen.findByRole('alert')
  expect(screen.getByLabelText('이메일').value).toBe('one@example.com')
  expect(screen.getByLabelText('닉네임').value).toBe('학습자')
  expect(screen.getByLabelText('비밀번호').value).toBe('')
  expect(screen.getByTestId('route').textContent).toBe('/signup')
})

test('login success moves to the private home with current nickname', async () => {
  open('/login')
  await screen.findByRole('heading', { name: '로그인' })
  type('이메일', 'one@example.com')
  type('비밀번호', crypto.randomUUID())
  fireEvent.click(screen.getByRole('button', { name: '로그인' }))
  await screen.findByText('학습자님, 반가워요.')
  expect(screen.getByTestId('route').textContent).toBe('/')
  expect(screen.getByRole('link', { name: '계정 설정' })).toBeTruthy()
})

test.each([401, 503])('login failure %s keeps email and clears password', async status => {
  accounts.login.mockRejectedValue(Object.assign(new Error('로그인 정보를 확인해 주세요.'), { status }))
  open('/login')
  await screen.findByRole('heading', { name: '로그인' })
  type('이메일', 'one@example.com')
  type('비밀번호', crypto.randomUUID())
  fireEvent.click(screen.getByRole('button', { name: '로그인' }))
  await screen.findByRole('alert')
  expect(screen.getByLabelText('이메일').value).toBe('one@example.com')
  expect(screen.getByLabelText('비밀번호').value).toBe('')
})

test('nickname failure preserves draft and saved nickname, then success updates the current user', async () => {
  accounts.readSession.mockResolvedValue(signedIn())
  accounts.changeNickname.mockRejectedValueOnce(Object.assign(new Error('이미 사용 중인 닉네임입니다.'), { status: 409 }))
    .mockResolvedValueOnce({ ...user, nickname: '새닉네임' })
  open('/settings')
  await screen.findByRole('heading', { name: '닉네임 변경' })
  type('새 닉네임', '이미있는이름')
  fireEvent.click(screen.getByRole('button', { name: '변경하기' }))
  await screen.findByRole('alert')
  expect(screen.getByLabelText('새 닉네임').value).toBe('이미있는이름')
  expect(screen.getByText('학습자')).toBeTruthy()
  type('새 닉네임', '새닉네임')
  fireEvent.click(screen.getByRole('button', { name: '변경하기' }))
  await screen.findByText('닉네임을 변경했어요.')
  expect(screen.getByText('새닉네임')).toBeTruthy()
  fireEvent.click(screen.getByRole('link', { name: '내 기록' }))
  await screen.findByText('새닉네임님, 반가워요.')
})

test('failed session bootstrap can be retried', async () => {
  accounts.readSession.mockRejectedValueOnce(new Error('연결할 수 없어요.')).mockResolvedValue(anonymous())
  open('/login')
  await screen.findByRole('alert')
  fireEvent.click(screen.getByRole('button', { name: '다시 연결' }))
  await screen.findByRole('heading', { name: '로그인' })
})

test('expired CSRF refreshes session without replaying the signup', async () => {
  accounts.signup.mockRejectedValue(Object.assign(new Error('다시 시도해 주세요.'), { status: 403 }))
  open('/signup')
  await screen.findByRole('heading', { name: '회원가입' })
  type('이메일', 'one@example.com')
  type('닉네임', '학습자')
  type('비밀번호', crypto.randomUUID())
  fireEvent.click(screen.getByRole('button', { name: '회원가입' }))
  await screen.findByRole('alert')
  await waitFor(() => expect(accounts.readSession).toHaveBeenCalledTimes(2))
  expect(accounts.signup).toHaveBeenCalledTimes(1)
  expect(screen.getByLabelText('비밀번호').value).toBe('')
})
