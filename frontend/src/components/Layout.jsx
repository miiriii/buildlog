import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext.jsx'

export default function Layout({ children }) {
  const { user } = useAuth()
  return (
    <div className="shell">
      <header className="site-header">
        <Link className="brand" to="/" aria-label="BuildLog 홈">
          <span className="brand-mark" aria-hidden="true">B<span>_</span></span>
          <span>BuildLog</span>
        </Link>
        {user ? <nav className="account-nav" aria-label="계정 메뉴">
          <NavLink to="/" end>내 기록</NavLink>
          <NavLink to="/settings">계정 설정</NavLink>
        </nav> : <span className="header-note">배움의 과정을 한곳에</span>}
      </header>
      {children}
      <footer>BuildLog <span aria-hidden="true">·</span> 배운 순간을, 나의 기록으로.</footer>
    </div>
  )
}
