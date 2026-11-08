export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.status = status
  }
}

export async function request(path, { method = 'GET', body, csrfToken } = {}) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 8000)
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      method, credentials: 'include', signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body ? { 'Content-Type': 'application/json' } : {}),
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) throw new ApiError(
      typeof data?.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.', response.status,
    )
    if (!data) throw new ApiError('응답을 확인하지 못했습니다.')
    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError('서비스에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.')
  } finally {
    clearTimeout(timeout)
  }
}

export async function getHealth(signal) {
  const response = await fetch(`${apiBaseUrl}/api/health`, {
    credentials: 'include',
    signal,
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error('서비스에 연결하지 못했습니다.')
  const health = await response.json()
  if (health.status !== 'ok' || health.service !== 'BuildLog') {
    throw new Error('서비스 상태를 확인하지 못했습니다.')
  }
  return health
}
