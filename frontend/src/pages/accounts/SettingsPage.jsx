import { useState } from 'react'
import { useAuth } from '../../auth/AuthContext.jsx'

export default function SettingsPage() {
  const { user, changeNickname } = useAuth()
  const [nickname, setNickname] = useState(user.nickname)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    setSuccess('')
    try {
      const updated = await changeNickname(nickname.trim())
      setNickname(updated.nickname)
      setSuccess('닉네임을 변경했어요.')
    } catch (reason) {
      setError(reason.message)
    } finally {
      setBusy(false)
    }
  }

  return <main className="settings-main">
    <p className="eyebrow">나의 계정</p><h1>계정 설정</h1>
    <p className="intro-copy">BuildLog에서 사용할 이름을 정해 주세요.</p>
    <section className="form-card settings-card" aria-labelledby="nickname-title">
      <h2 id="nickname-title">닉네임 변경</h2><p className="form-description">현재 닉네임: <strong>{user.nickname}</strong></p>
      <form onSubmit={submit} noValidate>
        <label htmlFor="settings-nickname">새 닉네임</label>
        <input id="settings-nickname" name="nickname" autoComplete="nickname" aria-describedby="settings-help" value={nickname} onChange={event => setNickname(event.target.value)} disabled={busy} required />
        <p className="field-help" id="settings-help">다른 사람과 겹치지 않는 한글·영문·숫자·밑줄 2~20자</p>
        {error && <p className="form-error" role="alert">{error}</p>}
        {success && <p className="form-success" role="status">{success}</p>}
        <button className="primary-button" type="submit" disabled={busy}>{busy ? '변경하는 중…' : '변경하기'}</button>
      </form>
    </section>
  </main>
}
