import { useEffect, useRef, useState } from 'react'
import { getMaterialAnalysis } from '../../api/materials.js'

const active = item => ['pending', 'processing'].includes(item.analysis?.status)

export function mergeAnalysis(items, id, analysis) {
  // Never insert a removed record or replace a newer response with an older one.
  return items.map(item => item.id === id && analysis.version > (item.analysis?.version ?? -1)
    ? { ...item, analysis } : item)
}

export function useMaterialAnalysis(items, filter, setItems, refreshSession, attempt) {
  const current = useRef(items)
  current.current = items
  const deadlines = useRef(new Map())
  const [message, setMessage] = useState('')
  const key = items.filter(item => active(item) && (filter === 'all' || item.media_type === filter))
    .map(item => item.id).sort((a, b) => a - b).join(',')

  useEffect(() => { deadlines.current.clear() }, [attempt])

  useEffect(() => {
    for (const id of deadlines.current.keys()) {
      if (!current.current.some(item => item.id === id && active(item))) deadlines.current.delete(id)
    }
    if (!key) return
    let cancelled = false, disposed = false, running = false, timer
    const controllers = new Set()
    const ids = key.split(',').map(Number)
    for (const id of ids) if (!deadlines.current.has(id)) deadlines.current.set(id, Date.now() + 120000)
    setMessage('')

    async function poll() {
      if (cancelled || running || document.hidden) return
      running = true
      let cursor = 0
      const candidates = ids.filter(id => current.current.some(item => item.id === id && active(item)))
      async function consume() {
        while (!cancelled && cursor < candidates.length) {
          const id = candidates[cursor++]
          if (Date.now() > deadlines.current.get(id)) {
            setMessage('요약 확인이 오래 걸리고 있어요. 목록 새로 확인으로 결과를 확인해 주세요.')
            continue
          }
          const controller = new AbortController()
          controllers.add(controller)
          try {
            const analysis = await getMaterialAnalysis(id, controller.signal)
            if (!cancelled) setItems(previous => mergeAnalysis(previous, id, analysis))
          } catch (error) {
            if (cancelled || error.name === 'AbortError') return
            cancelled = true
            controllers.forEach(value => value.abort())
            if (error.status === 401) {
              try { await refreshSession() } catch { /* No automatic replay. */ }
            }
            if (!disposed) setMessage(error.status === 404 ? '자료가 변경됐어요. 목록을 새로 확인해 주세요.'
              : '요약 상태를 확인하지 못했어요. 목록을 새로 확인해 주세요.')
          } finally { controllers.delete(controller) }
        }
      }
      await Promise.all([consume(), consume()])
      running = false
      if (!cancelled && candidates.some(id => Date.now() <= deadlines.current.get(id))) timer = setTimeout(poll, 3000)
    }
    function visibility() {
      clearTimeout(timer)
      if (!document.hidden) poll()
    }
    document.addEventListener('visibilitychange', visibility)
    poll()
    return () => { disposed = true; cancelled = true; clearTimeout(timer); controllers.forEach(value => value.abort()); document.removeEventListener('visibilitychange', visibility) }
  }, [key, setItems, refreshSession, attempt])
  return message
}
