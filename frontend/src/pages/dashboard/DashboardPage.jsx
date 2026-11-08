import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext.jsx'
import styles from './DashboardPage.module.css'

const studies = [
  { title: 'React 컴포넌트, 이제 조금 알 것 같아요', date: '오늘', description: '화면을 작은 조각으로 나누고 다시 조합하는 방법을 배웠어요.' },
  { title: 'FastAPI로 첫 API 만들기', date: '어제', description: 'GET과 POST의 차이를 직접 요청하며 확인했어요.' },
  { title: 'Supabase 연결 성공!', date: '10월 18일', description: '내가 쓴 기록이 새로고침 후에도 그대로 남아 있어요.' },
]

const initialTasks = [
  'Figma 대시보드 디자인 살펴보기',
  'MCP로 디자인 정보 읽어오기',
  'React 화면으로 구현하기',
  '실제 데이터 연결해보기',
]

const unavailableMenus = [
  { icon: '▤', label: '공부 기록' },
  { icon: '✓', label: '할 일' },
  { icon: '!', label: '오류 기록' },
  { icon: '↗', label: '공개 기록' },
]

function SummaryCard({ label, value, hint }) {
  return <div className={styles.summaryCard}>
    <dt>{label}</dt>
    <dd className={styles.summaryValue}>{value}</dd>
    <dd className={styles.summaryHint}>{hint}</dd>
  </div>
}

export default function DashboardPage() {
  const { user } = useAuth()
  const nickname = user.nickname
  const avatarInitial = Array.from(nickname)[0]
  const [checkedTasks, setCheckedTasks] = useState(() => initialTasks.map(() => false))
  const completed = 8 + checkedTasks.filter(Boolean).length
  const remaining = 12 - completed
  const percentage = Math.round(completed / 12 * 100)

  function toggleTask(index) {
    setCheckedTasks(previous => previous.map((checked, item) => item === index ? !checked : checked))
  }

  return <div className={styles.dashboard}>
    <aside className={styles.sidebar} aria-label="워크스페이스">
      <Link to="/" className={styles.brand} aria-label="BuildLog 홈">
        <span className={styles.brandMark} aria-hidden="true">b</span>
        <span>BuildLog</span>
      </Link>
      <p className={styles.workspaceLabel}>MY WORKSPACE</p>
      <nav className={styles.navigation} aria-label="대시보드 메뉴">
        <NavLink to="/dashboard" end className={styles.activeMenu}>
          <span className={styles.menuIcon} aria-hidden="true">▦</span>대시보드
        </NavLink>
        {unavailableMenus.map(menu => <button key={menu.label} className={styles.menuItem}
          type="button" disabled title="아직 연결할 페이지가 없습니다.">
          <span className={styles.menuIcon} aria-hidden="true">{menu.icon}</span>{menu.label}
        </button>)}
      </nav>
      <Link to="/settings" className={styles.account}>
        <span className={styles.avatar} aria-hidden="true">{avatarInitial}</span>
        <span className={styles.accountLabel}><strong title={nickname}>{nickname}</strong><span>계정 설정&nbsp; ›</span></span>
      </Link>
    </aside>

    <main className={styles.main}>
      <div className={styles.topbar}>
        <p>내 학습 한눈에 보기</p>
        <time dateTime="2026-10-20">2026. 10. 20&nbsp; 화요일</time>
      </div>

      <header className={styles.greeting}>
        <div><h1>{nickname}님, 차곡차곡 쌓이고 있어요</h1><p>오늘의 배움도 기록으로 남겨보세요.</p></div>
        <button className={styles.newStudy} type="button" disabled title="아직 연결할 공부 기록 작성 페이지가 없습니다.">+&nbsp; 공부 기록 쓰기</button>
      </header>

      <dl className={styles.summaries} aria-label="학습 요약">
        <SummaryCard label="공부 기록" value={24} hint="쌓아온 배움의 순간" />
        <SummaryCard label="남은 할 일" value={remaining} hint="하나씩 완료해보세요" />
        <SummaryCard label="미해결 오류" value={2} hint="해결 과정도 소중한 기록이에요" />
      </dl>

      <div className={styles.contentGrid}>
        <section className={styles.recentStudies} aria-labelledby="dashboard-studies-title">
          <div className={styles.sectionHeader}>
            <h2 id="dashboard-studies-title">최근 공부 기록</h2>
            <button className={styles.viewAll} type="button" disabled title="아직 연결할 공부 기록 목록이 없습니다.">전체 보기&nbsp; ›</button>
          </div>
          {studies.map((study, index) => <article className={styles.study} key={study.title}>
            {index > 0 && <hr className={styles.divider} />}
            <div className={styles.studyTitle}><h3>{study.title}</h3><span>{study.date}</span></div>
            <p>{study.description}</p>
          </article>)}
        </section>

        <section className={styles.tasks} aria-labelledby="dashboard-tasks-title">
          <div className={styles.taskHeader}>
            <h2 id="dashboard-tasks-title">남은 할 일</h2><span className={styles.taskBadge}>{remaining}개</span>
          </div>
          <p className={styles.taskHint}>작은 완료가 모여 큰 성장이 돼요.</p>
          <ul className={styles.taskList}>
            {initialTasks.map((task, index) => <li key={task}>
              <label className={styles.taskRow}>
                <input type="checkbox" checked={checkedTasks[index]} onChange={() => toggleTask(index)} />
                <span>{task}</span>
              </label>
            </li>)}
          </ul>
          <button className={styles.manageTasks} type="button" disabled title="아직 연결할 할 일 관리 페이지가 없습니다.">할 일 관리하기&nbsp; →</button>
        </section>
      </div>

      <section className={styles.completion} aria-label="할 일 완료 현황">
        <div className={styles.progressCopy}>
          <h2>잘하고 있어요. 벌써 {completed}개 완료!</h2>
          <p>전체 할 일 12개 중 {completed}개를 마쳤어요.</p>
        </div>
        <div className={styles.progressVisualization}>
          <div className={styles.progressLabels}><span id="dashboard-progress-label">할 일 완료율</span><strong>{percentage}%</strong></div>
          <div className={styles.progressTrack} role="progressbar" aria-labelledby="dashboard-progress-label"
            aria-valuemin={0} aria-valuemax={12} aria-valuenow={completed} aria-valuetext={`${percentage}%`}>
            <div className={styles.progressFill} style={{ width: `${completed / 12 * 100}%` }} />
          </div>
        </div>
        <p className={styles.progressCount}>{completed} / 12</p>
      </section>

      <footer className={styles.footer}>
        <span>매일의 작은 기록, 내일의 큰 변화.</span><span>수업용 예시 데이터</span>
      </footer>
    </main>
  </div>
}
