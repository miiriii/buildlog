import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { AppRoutes } from '../App.jsx'
import * as accounts from '../api/accounts.js'

vi.mock('../api/accounts.js', () => ({
  readSession: vi.fn(), signup: vi.fn(), login: vi.fn(), changeNickname: vi.fn(),
}))

const user = { id: 1, email: 'one@example.com', nickname: '학습자' }
const session = (currentUser = user) => ({ user: currentUser, csrf_token: crypto.randomUUID() })

function NavigationProbe() {
  const location = useLocation()
  const navigate = useNavigate()
  return <><span data-testid="route">{location.pathname}</span>
    <button onClick={() => navigate(-1)}>테스트 뒤로</button></>
}

function openDashboard() {
  return render(<MemoryRouter initialEntries={['/dashboard']}><AppRoutes /><NavigationProbe /></MemoryRouter>)
}

async function expectNickname(nickname) {
  await screen.findByRole('heading', { name: nickname + '님, 차곡차곡 쌓이고 있어요' })
  expect(screen.getByTitle(nickname).textContent).toBe(nickname)
  const account = screen.getByRole('link', { name: /계정 설정/ })
  expect(account.querySelector('[aria-hidden="true"]').textContent).toBe(Array.from(nickname)[0])
  expect(screen.queryByText('이월')).toBeNull()
}

beforeEach(() => {
  vi.resetAllMocks()
  accounts.readSession.mockResolvedValue(session())
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected direct API request') }))
})

afterEach(() => vi.unstubAllGlobals())

test.each(['학습자', '한글', '가'.repeat(20), 'Ab_123', 'A'.repeat(20), '12'])('shows session nickname %s in all three locations', async nickname => {
  accounts.readSession.mockResolvedValue(session({ ...user, nickname }))
  openDashboard()
  await expectNickname(nickname)
  expect(screen.getByLabelText('학습 요약').textContent).toContain('공부 기록24')
  expect(screen.getByText('4개')).toBeTruthy()
  expect(screen.getByText('2')).toBeTruthy()
  expect(screen.getByText('수업용 예시 데이터')).toBeTruthy()
  expect(accounts.readSession).toHaveBeenCalledTimes(1)
  expect(fetch).not.toHaveBeenCalled()
})

test('another session displays its own nickname without retaining the previous user', async () => {
  const page = openDashboard()
  await expectNickname(user.nickname)
  page.unmount()
  accounts.readSession.mockResolvedValue(session({ ...user, id: 2, nickname: '다른학습자' }))
  openDashboard()
  await expectNickname('다른학습자')
  expect(screen.queryByTitle(user.nickname)).toBeNull()
})

test('waits for session resolution without showing a sample name or redirecting early', async () => {
  let resolveSession
  accounts.readSession.mockReturnValue(new Promise(resolve => { resolveSession = resolve }))
  openDashboard()
  expect(screen.getByRole('status').textContent).toContain('로그인 상태를 확인')
  expect(screen.getByTestId('route').textContent).toBe('/dashboard')
  expect(screen.queryByRole('heading')).toBeNull()
  expect(screen.queryByText('이월')).toBeNull()
  await act(async () => { resolveSession(session()) })
  await expectNickname(user.nickname)
})

test('anonymous or expired sessions redirect to login instead of displaying the dashboard', async () => {
  accounts.readSession.mockResolvedValue(session(null))
  openDashboard()
  await screen.findByRole('heading', { name: '로그인' })
  expect(screen.getByTestId('route').textContent).toBe('/login')
  expect(screen.queryByLabelText('학습 요약')).toBeNull()
  expect(accounts.readSession).toHaveBeenCalledTimes(1)
})

test('session failure shows an error without redirecting and retry can restore the dashboard', async () => {
  accounts.readSession.mockRejectedValueOnce(new Error('서비스에 연결할 수 없어요.')).mockResolvedValue(session())
  openDashboard()
  await screen.findByRole('alert')
  expect(screen.getByTestId('route').textContent).toBe('/dashboard')
  expect(screen.queryByLabelText('학습 요약')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '다시 연결' }))
  await expectNickname(user.nickname)
  expect(accounts.readSession).toHaveBeenCalledTimes(2)
})

test.each([true, false])('nickname update success=%s remains correct after returning from settings', async succeeds => {
  const updated = { ...user, nickname: '새닉네임' }
  if (succeeds) accounts.changeNickname.mockResolvedValue(updated)
  else accounts.changeNickname.mockRejectedValue(Object.assign(new Error('이미 사용 중인 닉네임입니다.'), { status: 409 }))
  openDashboard()
  await expectNickname(user.nickname)
  fireEvent.click(screen.getByRole('link', { name: /계정 설정/ }))
  await screen.findByRole('heading', { name: '닉네임 변경' })
  fireEvent.change(screen.getByLabelText('새 닉네임'), { target: { value: updated.nickname } })
  fireEvent.click(screen.getByRole('button', { name: '변경하기' }))
  if (succeeds) await screen.findByText('닉네임을 변경했어요.')
  else await screen.findByRole('alert')
  fireEvent.click(screen.getByRole('button', { name: '테스트 뒤로' }))
  await expectNickname(succeeds ? updated.nickname : user.nickname)
  expect(accounts.readSession).toHaveBeenCalledTimes(1)
  expect(accounts.changeNickname).toHaveBeenCalledTimes(1)
  expect(fetch).not.toHaveBeenCalled()
})

test('checkboxes update only local counts and a fresh mount reloads the user and resets tasks', async () => {
  const page = openDashboard()
  await expectNickname(user.nickname)
  const checkbox = screen.getByRole('checkbox', { name: 'Figma 대시보드 디자인 살펴보기' })
  fireEvent.click(checkbox)
  expect(checkbox.checked).toBe(true)
  expect(screen.getByText('3개')).toBeTruthy()
  expect(screen.getByText('75%')).toBeTruthy()
  expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('9')
  fireEvent.click(checkbox)
  expect(screen.getByText('4개')).toBeTruthy()
  for (const item of screen.getAllByRole('checkbox')) fireEvent.click(item)
  expect(screen.getByText('0개')).toBeTruthy()
  expect(screen.getByText('100%')).toBeTruthy()
  expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('12')
  expect(accounts.changeNickname).not.toHaveBeenCalled()
  expect(accounts.login).not.toHaveBeenCalled()
  expect(accounts.signup).not.toHaveBeenCalled()
  page.unmount()
  accounts.readSession.mockResolvedValue(session({ ...user, nickname: '서버현재이름' }))
  openDashboard()
  await expectNickname('서버현재이름')
  expect(screen.getByText('67%')).toBeTruthy()
  expect(screen.getAllByRole('checkbox').every(item => !item.checked)).toBe(true)
  expect(accounts.readSession).toHaveBeenCalledTimes(2)
  expect(fetch).not.toHaveBeenCalled()
})

test('only implemented paths are linked and unavailable dashboard actions remain disabled', async () => {
  openDashboard()
  await expectNickname(user.nickname)
  expect(screen.getAllByRole('link').map(link => link.getAttribute('href')).sort())
    .toEqual(['/', '/dashboard', '/settings'])
  const navigation = screen.getByRole('navigation', { name: '대시보드 메뉴' })
  for (const button of within(navigation).getAllByRole('button')) expect(button.disabled).toBe(true)
  for (const name of ['공부 기록 쓰기', '전체 보기', '할 일 관리하기']) {
    expect(screen.getByRole('button', { name: new RegExp(name) }).disabled).toBe(true)
  }
})
