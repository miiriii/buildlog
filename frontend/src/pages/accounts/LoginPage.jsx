import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext.jsx'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await auth.login({ email: email.trim(), password })
      navigate('/', { replace: true })
    } catch (reason) {
      setError(reason.message)
    } finally {
      setPassword('')
      setBusy(false)
    }
  }

  return <main className="account-main">
    <section className="auth-intro"><p className="eyebrow">다시 만나 반가워요</p>
      <h1>오늘의 배움을<br />이어가 볼까요?</h1>
      <p className="intro-copy">작은 배움도 소중한 기록이 되도록.<br />나의 BuildLog로 돌아오세요.</p>
    </section>
    <section className="form-card" aria-labelledby="login-title">
      <h2 id="login-title">로그인</h2><p className="form-description">가입한 이메일로 로그인해 주세요.</p>
      {location.state?.notice && <p className="form-success" role="status">{location.state.notice}</p>}
      <form onSubmit={submit} noValidate>
        <label htmlFor="login-email">이메일</label>
        <input id="login-email" name="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} required />
        <label htmlFor="login-password">비밀번호</label>
        <input id="login-password" name="password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} required />
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy}>{busy ? '로그인하는 중…' : '로그인'}</button>
      </form>
      <p className="form-switch">아직 계정이 없나요? <Link to="/signup">회원가입</Link></p>
    </section>
  </main>
}
