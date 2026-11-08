import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import * as accounts from '../api/accounts.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    accounts.readSession().then(data => {
      if (active) setSession(data)
    }).catch(reason => {
      if (active) setError(reason.message)
    }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt])

  async function mutate(operation) {
    if (!session?.csrf_token) throw new Error('연결을 다시 확인해 주세요.')
    try {
      return await operation(session.csrf_token)
    } catch (reason) {
      if (reason.status === 401 || reason.status === 403) {
        // Refresh expired cookies/CSRF for the next attempt; do not replay writes.
        try { setSession(await accounts.readSession()) } catch { /* Preserve the original failure. */ }
      }
      throw reason
    }
  }

  const refreshSession = useCallback(async () => {
    const data = await accounts.readSession()
    setSession(data)
    return data
  }, [])

  const value = {
    user: session?.user ?? null,
    withSession: mutate,
    refreshSession,
    signup: values => mutate(token => accounts.signup(values, token)),
    login: async values => {
      const data = await mutate(token => accounts.login(values, token))
      setSession(data)
    },
    changeNickname: async nickname => {
      const user = await mutate(token => accounts.changeNickname(nickname, token))
      setSession(previous => ({ ...previous, user }))
      return user
    },
  }

  if (loading || error) return (
    <div className="connection-screen" role={error ? 'alert' : 'status'}>
      <strong>BuildLog</strong>
      <p>{loading ? '로그인 상태를 확인하고 있어요.' : error}</p>
      {error && <button type="button" onClick={() => setAttempt(value => value + 1)}>다시 연결</button>}
    </div>
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
