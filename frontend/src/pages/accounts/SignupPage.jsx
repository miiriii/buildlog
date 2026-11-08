import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext.jsx'

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [nickname, setNickname] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const auth = useAuth()
  const navigate = useNavigate()

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await auth.signup({ email: email.trim(), nickname: nickname.trim(), password })
      navigate('/login', { replace: true, state: { notice: '회원가입을 마쳤어요. 로그인해 주세요.' } })
    } catch (reason) {
      setError(reason.message)
    } finally {
      setPassword('')
      setBusy(false)
    }
  }

  return <main className="account-main">
    <section className="auth-intro"><p className="eyebrow">나의 기록, 여기서 시작</p>
      <h1>차곡차곡 쌓아갈<br />배움의 공간을 만들어요.</h1>
      <p className="intro-copy">이메일과 닉네임으로 나만의 기록을 시작하세요.<br />기록은 기본적으로 나에게만 보여요.</p>
    </section>
    <section className="form-card" aria-labelledby="signup-title">
      <h2 id="signup-title">회원가입</h2><p className="form-description">BuildLog에 오신 걸 환영해요.</p>
      <form onSubmit={submit} noValidate>
        <label htmlFor="signup-email">이메일</label>
        <input id="signup-email" name="email" type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} disabled={busy} required />
        <label htmlFor="signup-nickname">닉네임</label>
        <input id="signup-nickname" name="nickname" autoComplete="nickname" aria-describedby="nickname-help" value={nickname} onChange={event => setNickname(event.target.value)} disabled={busy} required />
        <p className="field-help" id="nickname-help">한글·영문·숫자·밑줄로 2~20자</p>
        <label htmlFor="signup-password">비밀번호</label>
        <input id="signup-password" name="password" type="password" autoComplete="new-password" aria-describedby="password-help" value={password} onChange={event => setPassword(event.target.value)} disabled={busy} required />
        <p className="field-help" id="password-help">8~64자로 입력해 주세요.</p>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="submit" disabled={busy}>{busy ? '가입하는 중…' : '회원가입'}</button>
      </form>
      <p className="form-switch">이미 계정이 있나요? <Link to="/login">로그인</Link></p>
    </section>
  </main>
}
