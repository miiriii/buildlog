import { request } from './client.js'

let pendingSession
export function readSession() {
  // StrictMode can mount twice; share the request so cookie and nonce stay paired.
  pendingSession ??= request('/api/accounts/session').finally(() => { pendingSession = undefined })
  return pendingSession
}
export const signup = (values, csrfToken) => request('/api/accounts/signup', { method: 'POST', body: values, csrfToken })
export const login = (values, csrfToken) => request('/api/accounts/login', { method: 'POST', body: values, csrfToken })
export const changeNickname = (nickname, csrfToken) => request('/api/accounts/me', { method: 'PATCH', body: { nickname }, csrfToken })
