import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext.jsx'
import * as materialsApi from '../../api/materials.js'
import styles from './MaterialsPage.module.css'
import { characterCount, normalizeTitle, titleError, memoError, inspectSelection, formatFileSize } from './validation.js'
import { mergeAnalysis, useMaterialAnalysis } from './useMaterialAnalysis.js'

const filters = [{ value: 'all', label: '전체' }, { value: 'image', label: '이미지' }, { value: 'video', label: '영상' }]
const nextStep = '다음 단계에서 연결'

function MaterialCard({ material, busy, onOpen, onDelete, onRetry }) {
  return <li className={styles.card}>
    <div className={`${styles.preview} ${material.media_type === 'video' ? styles.video : ''}`} aria-hidden="true">
      <strong>{material.media_type === 'video' ? '▶' : 'IMG'}</strong><span>{material.media_type === 'video' ? '영상 파일' : '이미지 파일'}</span>
    </div>
    <div className={styles.cardBody}>
      <h3>{material.title}</h3>
      {material.memo && <p className={styles.memo}>{material.memo}</p>}
      <p className={styles.filename}>{material.original_filename}</p>
      <p>{material.mime_type.split('/')[1].toUpperCase()} · {formatFileSize(material.size_bytes)}</p>
      <div className={styles.cardActions}>
        <time dateTime={material.created_at}>{new Date(material.created_at).toLocaleDateString('ko-KR')}</time>
        <button type="button" disabled={busy} onClick={() => onOpen(material)}>원본 보기</button>
        <button type="button" disabled={busy} onClick={() => onDelete(material)}>삭제</button>
      </div>
      <div className={styles.summary} aria-label={`${material.title} AI 요약`}>
        <strong>AI 요약</strong>
        {(!material.analysis || material.analysis.status === 'not_requested') && <p>기존 자료는 자동 분석하지 않아요.</p>}
        {material.analysis?.status === 'pending' && <p role="status">요약 대기 중이에요.</p>}
        {material.analysis?.status === 'processing' && <p role="status">자료 내용을 요약하고 있어요.</p>}
        {material.analysis?.status === 'succeeded' && <><p className={styles.summaryText}>{material.analysis.summary}</p>
          <small>AI 요약에는 오류가 있을 수 있어요. 원본과 함께 확인하세요.</small>
          {material.analysis.scope?.kind === 'video_frames' && <small>영상 화면 {material.analysis.scope.frame_count}장 기준 · 음성 미포함</small>}</>}
        {material.analysis?.status === 'failed' && <><p>{material.analysis.error_message || '요약을 완료하지 못했어요. 원본은 저장돼 있어요.'}</p>
          {material.analysis.can_retry && <button type="button" disabled={busy} onClick={() => onRetry(material)}>다시 요약</button>}</>}
      </div>
    </div>
  </li>
}

export default function MaterialsPage() {
  const auth = useAuth()
  return <MaterialsWorkspace key={auth.user.id} auth={auth} />
}

function OriginalViewer({ preview, onClose }) {
  const [error, setError] = useState(false)
  return <section className={styles.original} aria-label="자료 원본">
    <div className={styles.originalHeader}><h2>{preview.material.title}</h2><button type="button" onClick={onClose}>원본 닫기</button></div>
    {preview.material.media_type === 'image'
      ? <img src={preview.url} alt={preview.material.title} onError={() => setError(true)} />
      : <video src={preview.url} controls preload="metadata" onError={() => setError(true)} />}
    {error && <p role="alert">이 브라우저에서 원본을 표시하지 못했습니다. 파일을 내려받아 확인해 주세요.</p>}
    <a href={preview.url} download={preview.material.original_filename}>원본 파일 내려받기</a>
  </section>
}

function MaterialsWorkspace({ auth }) {
  const { user, withSession, refreshSession } = auth
  const [items, setItems] = useState([])
  const [listStatus, setListStatus] = useState('loading')
  const [listError, setListError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [actionError, setActionError] = useState('')
  const [preview, setPreview] = useState(null)
  const actionLock = useRef(false)
  const alive = useRef(true)
  const controllers = useRef(new Set())
  const [filter, setFilter] = useState('all')
  const [title, setTitle] = useState('')
  const [memo, setMemo] = useState('')
  const [titleTouched, setTitleTouched] = useState(false)
  const [selection, setSelection] = useState(null)
  const [fileError, setFileError] = useState('')
  const fileInput = useRef(null)
  const invalidTitle = titleTouched ? titleError(title) : ''
  const invalidMemo = memoError(memo)
  const visibleMaterials = items.filter(material => filter === 'all' || material.media_type === filter)
  const analysisNotice = useMaterialAnalysis(items, filter, setItems, refreshSession, attempt)

  useEffect(() => {
    alive.current = true
    return () => { alive.current = false; controllers.current.forEach(controller => controller.abort()) }
  }, [])

  useEffect(() => {
    let active = true
    const controller = new AbortController()
    setListStatus('loading'); setListError('')
    materialsApi.getMaterials(controller.signal).then(data => {
      if (active) {
        setItems(previous => data.map(item => {
          const newer = previous.find(saved => saved.id === item.id && (saved.analysis?.version ?? -1) > (item.analysis?.version ?? -1))
          return newer ? { ...item, analysis: newer.analysis } : item
        }))
        setListStatus('ready')
      }
    }).catch(async reason => {
      if (!active || reason.name === 'AbortError') return
      if (reason.status === 401) {
        try { await refreshSession() } catch { /* Preserve the error; no replay. */ }
      }
      if (active) { setListError(reason.message); setListStatus('error') }
    })
    return () => { active = false; controller.abort() }
  }, [attempt, refreshSession])

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview.url) }, [preview])

  function beginAction() {
    if (actionLock.current || listStatus !== 'ready') return null
    actionLock.current = true
    const controller = new AbortController()
    controllers.current.add(controller)
    setBusy(true); setNotice(''); setActionError('')
    return controller
  }

  function finishAction(controller) {
    controllers.current.delete(controller)
    actionLock.current = false
    if (alive.current) setBusy(false)
  }

  async function submit(event) {
    event.preventDefault(); setTitleTouched(true)
    if (titleError(title) || memoError(memo)) return
    if (!selection) { setFileError('파일을 한 개 선택해 주세요.'); return }
    const controller = beginAction()
    if (!controller) return
    try {
      const item = await withSession(token => materialsApi.uploadMaterial({ title: normalizeTitle(title), memo, file: selection.file }, token, controller.signal))
      if (!alive.current) return
      setItems(previous => [item, ...previous.filter(saved => saved.id !== item.id)])
      setTitle(''); setMemo(''); setSelection(null); setTitleTouched(false); setFileError('')
      setFilter('all'); setNotice('자료를 저장했어요.')
    } catch (reason) {
      if (alive.current && reason.name !== 'AbortError') setActionError(reason.message)
    } finally { finishAction(controller) }
  }

  async function openOriginal(material) {
    const controller = beginAction()
    if (!controller) return
    try {
      const blob = await materialsApi.getOriginal(material, controller.signal)
      if (alive.current) setPreview({ material, url: URL.createObjectURL(blob) })
    } catch (reason) {
      if (reason.status === 401 && alive.current) {
        try { await refreshSession() } catch { /* No automatic retry. */ }
      }
      if (alive.current && reason.name !== 'AbortError') setActionError(reason.message)
    } finally { finishAction(controller) }
  }

  async function removeMaterial(material) {
    if (actionLock.current || listStatus !== 'ready' || !window.confirm(`‘${material.title}’ 자료를 삭제할까요? 원본 파일도 삭제됩니다.`)) return
    const controller = beginAction()
    if (!controller) return
    try {
      await withSession(token => materialsApi.deleteMaterial(material.id, token, controller.signal))
      if (!alive.current) return
      setItems(previous => previous.filter(item => item.id !== material.id))
      setPreview(previous => previous?.material.id === material.id ? null : previous)
      setNotice('자료를 삭제했어요.')
    } catch (reason) {
      if (alive.current && reason.name !== 'AbortError') {
        setActionError(reason.status === 404 ? '자료가 없거나 접근할 수 없습니다. 목록을 다시 확인합니다.' : reason.message)
        if (reason.status === 404) setAttempt(value => value + 1)
      }
    } finally { finishAction(controller) }
  }

  async function retryAnalysis(material) {
    if (actionLock.current || !window.confirm('다시 요약할까요? OpenAI 사용 비용이 발생할 수 있습니다.')) return
    const controller = beginAction()
    if (!controller) return
    try {
      const analysis = await withSession(token => materialsApi.retryMaterialAnalysis(material.id, token, controller.signal))
      if (alive.current) {
        setItems(previous => mergeAnalysis(previous, material.id, analysis))
        setNotice('요약 요청을 접수했어요.')
      }
    } catch (reason) {
      if (alive.current && reason.name !== 'AbortError') setActionError(reason.message)
    } finally { finishAction(controller) }
  }

  function selectFile(event) {
    const files = Array.from(event.target.files || [])
    // Cancelling the picker must preserve the previous selection.
    if (!files.length) return
    const result = inspectSelection(files)
    setSelection(result.file ? result : null)
    setFileError(result.error)
    setNotice('')
    // Keep the File in React state and allow choosing the same file again.
    event.target.value = ''
  }

  return <div className={styles.materials}>
    <aside className={styles.sidebar} aria-label="워크스페이스">
      <Link to="/" className={styles.brand}><span aria-hidden="true">b</span> BuildLog</Link>
      <p className={styles.workspace}>MY WORKSPACE</p>
      <nav className={styles.nav} aria-label="학습 자료함 메뉴">
        <Link to="/dashboard">대시보드</Link>
        {['공부 기록', '할 일', '오류 기록'].map(label => <button type="button" key={label} disabled title={nextStep}>{label}</button>)}
        <Link to="/materials" className={styles.selected} aria-current="page">학습 자료함</Link>
        <button type="button" disabled title={nextStep}>공개 기록</button>
      </nav>
      <div className={styles.workspaceNote}><strong>나만의 학습 공간</strong><p>올린 자료는<br />나에게만 보여요.</p></div>
      <Link to="/settings" className={styles.account}>{user.nickname} · 내 계정</Link>
    </aside>

    <main className={styles.main}>
      <header className={styles.heading}>
        <p>MY LEARNING LIBRARY</p><h1>학습 자료함</h1>
        <span>캡처부터 실습 영상까지, 배운 순간을 한곳에 모아보세요.</span>
      </header>
      {actionError && <p className={styles.fieldError} role="alert">{actionError}</p>}
      {notice && <p className={styles.success} role="status">{notice}</p>}
      {busy && <p className={styles.hint} role="status">자료를 처리하고 있어요. 잠시 기다려 주세요.</p>}
      {preview && <OriginalViewer key={preview.url} preview={preview} onClose={() => setPreview(null)} />}
      <div className={styles.columns}>
        <section className={styles.registration} aria-labelledby="materials-register-title">
          <h2 id="materials-register-title">새 자료 등록</h2>
          <p className={styles.description}>기억하고 싶은 자료를 남겨보세요.</p>
          <form onSubmit={submit}>
            <label htmlFor="material-title">자료 제목</label>
            <input id="material-title" type="text" placeholder="예: REST API 수업 정리" disabled={busy}
              value={title} onChange={event => { setTitle(event.target.value); setTitleTouched(true) }}
              onBlur={() => { setTitle(normalizeTitle(title)); setTitleTouched(true) }}
              aria-invalid={!!invalidTitle} aria-describedby="material-title-help material-title-error" />
            <p id="material-title-help" className={styles.fieldHint}>앞뒤 공백 제외 {characterCount(normalizeTitle(title))} / 100자</p>
            <p id="material-title-error" className={styles.fieldError} role={invalidTitle ? 'alert' : undefined}>{invalidTitle}</p>
            <label htmlFor="material-memo">메모 · 선택</label>
            <textarea id="material-memo" placeholder="어떤 내용인지 간단히 적어주세요." rows={2} disabled={busy}
              value={memo} onChange={event => setMemo(event.target.value)} aria-invalid={!!invalidMemo}
              aria-describedby="material-memo-help material-memo-error" />
            <p id="material-memo-help" className={styles.fieldHint}>{characterCount(memo)} / 1,000자</p>
            <p id="material-memo-error" className={styles.fieldError} role={invalidMemo ? 'alert' : undefined}>{invalidMemo}</p>
            <div className={styles.fileArea}>
              <span className={styles.uploadIcon} aria-hidden="true">↑</span>
              <strong>이미지 또는 영상을 선택하세요</strong>
              <span>PNG · JPG(JPEG) 최대 5MiB / MP4 최대 30MiB</span>
              <input ref={fileInput} id="material-file" type="file" hidden aria-label="자료 파일" disabled={busy}
                accept=".png,.jpg,.jpeg,.mp4,image/png,image/jpeg,video/mp4" onChange={selectFile} />
              <button className={styles.primary} type="button" disabled={busy} onClick={() => fileInput.current.click()}
                aria-describedby="material-file-error">파일 선택</button>
            </div>
            <p id="material-file-error" className={styles.fieldError} role={fileError ? 'alert' : undefined}>{fileError}</p>
            {selection && <div className={styles.selection} role="status" aria-live="polite">
              <strong>선택한 파일 · 아직 저장되지 않았어요</strong>
              <p>{selection.file.name}</p><p>{selection.label} · {formatFileSize(selection.file.size)}</p>
            </div>}
            <p className={styles.hint}>자료당 파일 1개 · 나만 볼 수 있어요</p>
            <button className={`${styles.primary} ${styles.upload}`} type="submit"
              disabled={busy || listStatus !== 'ready' || !!titleError(title) || !!invalidMemo || !selection}>자료 업로드</button>
            <p className={styles.hint}>업로드 버튼을 누르면 선택한 파일과 내용을 저장합니다.</p>
            <p className={styles.hint}>저장한 이미지와 영상의 일부 화면을 OpenAI에 보내 자동 요약합니다. 음성은 보내지 않아요.</p>
          </form>
        </section>

        <section className={styles.library} aria-labelledby="materials-list-title">
          <div className={styles.libraryHeader}><h2 id="materials-list-title">내 자료 <span>{items.length}</span></h2>
            <button type="button" disabled={busy || listStatus === 'loading'} onClick={() => setAttempt(value => value + 1)}>목록 새로 확인</button></div>
          <p className={styles.exampleLabel}>나만 볼 수 있는 비공개 자료입니다.</p>
          {analysisNotice && <p className={styles.hint} role="status">{analysisNotice}</p>}
          <div className={styles.filters} role="group" aria-label="자료 종류 필터">
            {filters.map(item => <button type="button" key={item.value} aria-pressed={filter === item.value}
              onClick={() => setFilter(item.value)}>{item.label} {item.value === 'all' ? items.length : items.filter(saved => saved.media_type === item.value).length}</button>)}
          </div>
          {listStatus === 'loading' && <p role="status">자료를 불러오고 있어요.</p>}
          {listStatus === 'error' && <div role="alert"><p>{listError}</p><button type="button" onClick={() => setAttempt(value => value + 1)}>다시 불러오기</button></div>}
          {listStatus === 'ready' && !visibleMaterials.length && <p className={styles.empty}>{items.length ? '이 종류의 자료가 없어요.' : '아직 등록한 자료가 없어요. 첫 자료를 남겨보세요.'}</p>}
          <ul className={styles.cards} aria-label="내 자료 목록">{visibleMaterials.map(material => <MaterialCard key={material.id} material={material}
            busy={busy || listStatus !== 'ready'} onOpen={openOriginal} onDelete={removeMaterial} onRetry={retryAnalysis} />)}</ul>
          <p className={styles.encouragement}>차곡차곡 쌓인 자료가 나만의 복습 노트가 됩니다.</p>
        </section>
      </div>

      <section className={styles.ai} aria-labelledby="materials-ai-title">
        <div><h2 id="materials-ai-title">AI 학습 도우미 · 자동 요약</h2>
          <p>자료를 저장하면 각 자료 카드에 핵심 내용의 요약이 표시돼요.</p>
          <small>영상은 최대 8장의 화면만 분석합니다. 원본 보기와 삭제는 요약 중에도 사용할 수 있어요.</small></div>
      </section>
      <footer className={styles.footer}>나의 배움과 실습 자료를 안전하게 모아보세요.</footer>
    </main>
  </div>
}
