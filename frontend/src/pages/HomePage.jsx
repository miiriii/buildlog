import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getHealth } from '../api/client.js'
import { useAuth } from '../auth/AuthContext.jsx'

export default function HomePage() {
  const { user } = useAuth()
  const [status, setStatus] = useState('loading')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 8000)
    let active = true
    setStatus('loading')
    getHealth(controller.signal)
      .then(() => { if (active) setStatus('connected') })
      .catch(() => { if (active) setStatus('error') })
      .finally(() => clearTimeout(timeout))
    return () => { active = false; clearTimeout(timeout); controller.abort() }
  }, [attempt])

  return (
      <main>
        <section className="intro" aria-labelledby="welcome-title">
          <p className="eyebrow">{user.nickname}님, 반가워요.</p>
          <h1 id="welcome-title">오늘의 배움이<br />내일의 밑거름이 되도록.</h1>
          <p className="intro-copy">공부한 내용도, 앞으로 할 일도, 어렵게 풀어낸 오류도.<br className="desktop-break" /> 흩어져 있던 나의 기록을 BuildLog에서 모아보세요.</p>
        </section>
        <section className="welcome-card" aria-labelledby="getting-ready">
          <div className="card-icon" aria-hidden="true">✎</div>
          <div className="card-copy">
            <p className="eyebrow">작은 시작</p>
            <h2 id="getting-ready">기록을 위한 공간을 준비하고 있어요.</h2>
            <p>곧 이곳에서 공부와 프로젝트의 과정을 남길 수 있어요.</p>
            <p><Link to="/materials">학습 자료함</Link></p>
          </div>
          <div className={`connection ${status}`} role="status" aria-live="polite">
            <span className="status-dot" aria-hidden="true" />
            <span>{status === 'loading' ? '연결 확인 중' : status === 'connected' ? '서비스 연결 완료' : '서비스에 연결할 수 없어요'}</span>
            {status === 'error' && <button type="button" onClick={() => setAttempt(value => value + 1)}>다시 확인</button>}
          </div>
        </section>
      </main>
  )
}
