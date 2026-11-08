import { ApiError, apiBaseUrl } from './client.js'

const allowedTypes = new Set(['image/png', 'image/jpeg', 'video/mp4'])

function validMaterial(item) {
  return item && Number.isInteger(item.id) && item.id > 0 && typeof item.title === 'string'
    && (item.memo === null || typeof item.memo === 'string') && typeof item.original_filename === 'string'
    && ['image', 'video'].includes(item.media_type) && allowedTypes.has(item.mime_type)
    && Number.isInteger(item.size_bytes) && item.size_bytes > 0 && Number.isFinite(Date.parse(item.created_at))
    && (item.analysis === undefined || validAnalysis(item.analysis))
}

async function requestMaterial(path, { method = 'GET', body, csrfToken, signal, timeoutMs = 15000, expected = 200, binary = false } = {}) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (signal?.aborted) abort()
  else signal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(abort, timeoutMs)
  try {
    const response = await fetch(`${apiBaseUrl}/api/materials${path}`, {
      method, credentials: 'include', cache: 'no-store', signal: controller.signal,
      headers: { Accept: binary ? 'image/png, image/jpeg, video/mp4' : 'application/json',
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}) },
      ...(body ? { body } : {}), // FormData sets its own Content-Type and boundary.
    })
    if (!response.ok) {
      const data = await response.json().catch(() => null)
      throw new ApiError(typeof data?.detail === 'string' ? data.detail : '요청을 처리하지 못했습니다.', response.status)
    }
    if (response.status !== expected) throw new ApiError('서버의 처리 결과를 확인하지 못했습니다.')
    if (expected === 204) return
    return binary ? await response.blob() : await response.json()
  } catch (error) {
    if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError')
    if (error instanceof ApiError) throw error
    throw new ApiError(method === 'GET' ? '자료를 불러오지 못했습니다. 연결을 확인한 뒤 다시 시도해 주세요.'
      : '처리 결과를 확인하지 못했습니다. 목록을 새로 확인한 뒤 다시 시도해 주세요.')
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', abort)
  }
}

export async function getMaterials(signal) {
  const data = await requestMaterial('', { signal })
  if (!Array.isArray(data?.items) || !data.items.every(validMaterial)) throw new ApiError('자료 목록 응답을 확인하지 못했습니다.')
  return data.items
}

export async function uploadMaterial({ title, memo, file }, csrfToken, signal) {
  const body = new FormData()
  body.append('title', title)
  if (memo) body.append('memo', memo)
  body.append('file', file)
  const item = await requestMaterial('', { method: 'POST', body, csrfToken, signal, expected: 201, timeoutMs: 180000 })
  if (!validMaterial(item)) throw new ApiError('저장 결과를 확인하지 못했습니다. 목록을 새로 확인해 주세요.')
  return item
}

export const deleteMaterial = (id, csrfToken, signal) => requestMaterial(`/${id}`, { method: 'DELETE', csrfToken, signal, expected: 204 })

const analysisStates = new Set(['not_requested', 'pending', 'processing', 'succeeded', 'failed'])
export function validAnalysis(data) {
  return data && analysisStates.has(data.status) && Number.isInteger(data.version) && data.version >= 0
    && Number.isInteger(data.attempt_count) && data.attempt_count >= 0 && data.attempt_count <= 3
    && typeof data.can_retry === 'boolean' && (data.summary === null || typeof data.summary === 'string')
    && (data.status !== 'succeeded' || (typeof data.summary === 'string' && data.summary.trim().length > 0))
    && (data.error_message === null || typeof data.error_message === 'string')
    && (data.scope === null || (data.scope && ['image', 'video_frames'].includes(data.scope.kind)
      && Number.isInteger(data.scope.frame_count) && data.scope.frame_count >= 1 && data.scope.frame_count <= 8
      && Array.isArray(data.scope.timestamps) && data.scope.timestamps.every(Number.isFinite)
      && data.scope.audio_included === false))
}

export async function getMaterialAnalysis(id, signal) {
  const data = await requestMaterial(`/${id}/analysis`, { signal })
  if (!validAnalysis(data)) throw new ApiError('요약 응답을 확인하지 못했습니다.')
  return data
}

export async function retryMaterialAnalysis(id, csrfToken, signal) {
  const data = await requestMaterial(`/${id}/analysis/retry`, { method: 'POST', csrfToken, signal, expected: 202 })
  if (!validAnalysis(data)) throw new ApiError('요약 접수 결과를 확인하지 못했습니다. 목록을 다시 확인해 주세요.')
  return data
}

export async function getOriginal(material, signal) {
  const blob = await requestMaterial(`/${material.id}/file`, { signal, binary: true, timeoutMs: 120000 })
  if (blob.type !== material.mime_type || blob.size !== material.size_bytes) throw new ApiError('원본 파일 응답을 확인하지 못했습니다. 목록을 새로 확인해 주세요.')
  return blob
}
