# BuildLog 개발 환경과 실행 기준

## 1. 문서 상태

- 확인일: 2026-10-22 (한국 시간)
- 현재 단계: Phase 0 — 개발 기준과 환경 확인 완료
- 다음 단계: Phase 1 — FastAPI·React 프로젝트 뼈대 만들기
- 이 문서는 점검 결과와 앞으로 사용할 설정·명령을 기록합니다. 아래 설치·실행 명령은 아직 실행하지 않았습니다.
- Phase 0에서는 기존 문서와 도구를 읽고, 공개 패키지 정보와 공식 문서를 조회했습니다. 패키지 설치, 가상환경 생성, 기능 코드 작성, DB 생성·접속, Git 초기화·커밋은 하지 않았습니다.

## 2. 문서와 기능 범위 확인

`PRD.md`는 만들 기능의 범위, `spec.md`는 기능별 동작과 확인 방법, `plan.md`는 개발 순서를 설명합니다. `mvp.md`의 초기 미정 항목은 이후 확정된 PRD와 spec의 규칙을 따릅니다.

| 확인 대상 | 확인한 기준 | 결과 |
| --- | --- | --- |
| 서비스 구성 | 여러 사용자가 가입하고 각자의 기록 관리 | 일치 |
| 회원 | 이메일 로그인, 비밀번호 8~64자, 중복 없는 닉네임과 변경 | 일치. 입력 세부 조건은 spec 기준 |
| 공부 기록 | 제목 1~100자, 내용 1~5,000자, 작성·목록·읽기·검색·수정·삭제 | 일치 |
| 할 일 | 제목 1~100자, 완료·취소, 상태별 보기, 미완료 우선·같은 상태 최신순 | 일치 |
| 오류 기록 | 제목 1~100자, 오류 내용·입력한 해결 방법 1~5,000자, 검색·필터·상태 전환 | 초기 상태 문구를 사용자 답변으로 정리 |
| 공개 범위 | 기본 비공개, 본인만 변경, 공개 기록도 로그인한 사용자만 조회 | 일치 |
| 공개 검색 | 공부 제목·내용, 할 일 제목, 오류 제목·오류 내용·해결 방법 | 일치. 내 할 일 검색과 구분 |
| 댓글 | 공개 공부·오류에만 제공, 1~500자, 작성자 수정·삭제, 기록 작성자 삭제 | 일치 |
| 좋아요 | 공개 공부·오류에만 제공, 사용자당 한 번, 다시 누르면 취소 | 일치 |
| 신고 | 공개 기록·댓글, 이유 1~500자, 중복 방지, 운영자만 조회, 자동 삭제 없음 | 일치 |
| 화면 | 밝은 카드형 화면, 너비 360px 이상, Chrome·Edge·Safari 최신 두 버전 | 일치. 실제 화면 검증은 해당 개발 단계에서 수행 |
| 기술 | React → FastAPI → DB, 운영 Supabase PostgreSQL, 우선 로컬·테스트 SQLite3 | 일치 |

### 사용자 답변으로 정리한 내용

2026-10-22에 오류 기록의 초기 상태를 다음과 같이 확정했습니다.

- 기본값은 미해결입니다.
- 사용자가 해결 상태를 선택하고 해결 방법을 입력하면 처음부터 해결 상태로도 저장할 수 있습니다.
- 해결 방법만 입력했다고 자동으로 해결 처리하지 않습니다. 사용자가 선택한 상태를 따릅니다.
- 처음부터 해결 상태로 저장하면 해결 날짜와 시간도 함께 저장합니다.

`spec.md`의 “새 오류는 미해결로 저장” 문구와 `plan.md`의 관련 작업을 기본값에 대한 설명으로 맞추고, PRD에도 같은 기준을 반영했습니다. `plan.md`의 할 일 검색 제외 표현은 “내 할 일 검색”으로 명확히 했습니다. 공개 할 일 검색은 원래 계획대로 Phase 8에서 만듭니다.

이번 확인에서 남은 기능 범위 충돌은 없습니다. 새 기능은 추가하지 않았습니다.

### 첫 버전에서 만들지 않는 기능

- 이메일 확인
- 비밀번호 찾기
- 할 일 마감일과 중요도
- 내 할 일 검색
- 댓글 답글

신고 처리 상태, 신고에 따른 자동 삭제도 기존 요구사항대로 추가하지 않습니다.

## 3. 현재 컴퓨터에서 확인한 결과

| 항목 | 실제 확인 결과 | 프로젝트에서 사용할 기준 |
| --- | --- | --- |
| 운영 환경 | Windows, PowerShell 5.1.19041.6456 | PowerShell에서 직접 실행 가능한 명령 사용 |
| 기본 Python | 3.15.0 | 기본 설정은 변경하지 않음 |
| 별도 설치된 Python | CPython 3.14.6, 64비트 | 이 인터프리터로 프로젝트 가상환경 생성 예정 |
| Python 선택 명령 | `py -V:Astral/CPython3.14.6` 실행 성공 | 명시적으로 이 Python을 선택 |
| 가상환경 도구 | `venv`, `ensurepip` 모듈 사용 가능, pip 존재 | 추가 Python 설치 없이 Phase 1 시작 가능 |
| SQLite3 | Python 3.14.6에서 `sqlite3` import 성공, 연결 라이브러리 3.53.1 | 별도 SQLite 서버 설치 불필요 |
| Node.js | v24.22.0 | 현재 설치 버전 사용 |
| npm | 11.19.1, `npm.cmd --version` 실행 성공 | Windows 명령은 `npm.cmd` 사용 |
| PowerShell 실행 정책 | 유효 정책 `Restricted` | 활성화 스크립트 대신 가상환경의 `python.exe` 직접 사용. 정책 변경 불필요 |
| 포트 5173·8000 | 점검 시점에 수신 중인 프로세스 없음 | Phase 1 실행 전에 다시 확인 |
| 프로젝트 산출물 | `backend`, `frontend`, `database` 폴더는 비어 있음 | 아직 서버나 앱이 만들어지지 않은 상태 |
| Git·비밀 설정 | `.git`, 실제 `.env` 없음 | 초기화·비밀 설정 생성은 수행하지 않음 |

Python 3.14.6은 이미 설치되어 있고, 아래 주요 패키지의 Python 요구조건 및 Windows용 배포 파일을 확인할 수 있어 프로젝트 기준으로 선택했습니다. 전역 기본 Python을 바꾸지 않습니다.

SQLite3는 모듈과 라이브러리 버전만 읽었습니다. 이 단계에서는 메모리 DB를 포함해 DB 연결을 열거나 파일·테이블을 만들지 않았습니다. 실제 저장과 외래키 동작은 Phase 2 이후에 확인합니다.

## 4. 패키지 버전 기준과 확인 수준

아래는 2026-10-22에 PyPI와 npm 공식 레지스트리의 안정 배포 버전 및 요구조건을 조회하여 정한 설치 후보입니다. 아직 프로젝트에 설치된 버전은 아닙니다.

| 역할 | 설치 후보 버전 | 준비 단계 |
| --- | --- | --- |
| API | FastAPI 0.159.1 | Phase 1 |
| 실행 서버 | Uvicorn 0.54.0 | Phase 1 |
| 입력·응답 검사 | Pydantic 2.14.1 | Phase 1 |
| 환경 설정 | pydantic-settings 2.16.1 | Phase 1 |
| DB 접근 | SQLAlchemy 2.1.6, 동기식 세션 | Phase 2 |
| DB 구조 변경 | Alembic 1.20.0 | Phase 2 |
| 비밀번호 해시 | pwdlib[argon2] 0.3.1 | Phase 2 |
| 이메일 형식 검사 | email-validator 2.3.0 | Phase 3 |
| 서명 쿠키 | Starlette SessionMiddleware와 itsdangerous 2.2.0 | Phase 3 |
| 백엔드 테스트 | pytest 9.1.1, HTTPX 0.28.1 | Phase 1부터 필요한 테스트에 사용 |
| 화면 | React·React DOM 19.3.1 | Phase 1 |
| 프론트 개발·빌드 | Vite 8.3.5, @vitejs/plugin-react 6.1.2 | Phase 1 |
| 화면 테스트 | Vitest 5.0.5, @testing-library/react 16.3.3, @testing-library/dom 10.4.2, jsdom 30.1.3 | Phase 1부터 필요한 테스트에 사용 |
| PostgreSQL 연결 | psycopg[binary] 3.3.6 | Supabase 연결 검증 전 |

확인한 내용은 다음과 같습니다.

- Python 패키지의 선언된 Python 최소 버전이 선택한 Python 3.14.6을 허용합니다.
- Pydantic Core, SQLAlchemy, Argon2 바인딩 및 Psycopg Binary에서 Python 3.14 Windows 환경에 맞는 wheel 배포를 확인했습니다.
- Alembic 1.20.0은 SQLAlchemy 2.0 이상을 요구하므로 선택한 2.1.6이 조건에 맞습니다.
- React DOM의 React 요구조건과 React Testing Library의 React 19 지원 범위를 확인했습니다.
- Vite, React 플러그인, Vitest와 jsdom의 Node.js 요구조건이 현재 Node.js 24.22.0을 허용합니다. React 플러그인과 Vitest의 Vite 요구조건도 확인했습니다.
- FastAPI와 함께 설치할 Starlette, Pydantic 등의 최종 조합은 Phase 1의 실제 의존성 해결과 API 테스트로 확인합니다.

이 결과는 메타데이터에 대한 호환성 확인입니다. 설치 성공이나 앱 실행·통합 테스트 통과를 의미하지 않습니다. 실제 설치 단계에서 필요한 패키지만 설치하고, 해결된 정확한 버전은 `backend/requirements.txt`와 `frontend/package-lock.json`에 기록합니다. 후보 버전을 바꿔야 하면 이유와 결과를 문서에 남깁니다.

## 5. 개발 주소와 환경 변수

| 구분 | 기준 |
| --- | --- |
| React 화면 | `http://localhost:5173` |
| FastAPI 서버 | `http://localhost:8000` |
| API 경로 | 기능 API는 `/api` 아래에 연결 예정 |
| 상태 확인 | Phase 1에서 `/api/health` 제공 예정 |
| 개발용 DB 파일 | 프로젝트 루트 기준 `database/buildlog.sqlite3` |
| 자동 테스트 DB | pytest가 만든 임시 폴더의 별도 SQLite3 DB |
| 백엔드 설정 파일 | 프로젝트 루트 `.env`, 항목 공유는 루트 `.env.example` |
| 프론트 설정 파일 | `frontend/.env`, 항목 공유는 `frontend/.env.example` |

프론트와 API 주소의 호스트 표기는 `localhost`로 통일합니다. `localhost`와 `127.0.0.1`을 섞어 쿠키와 허용 출처가 어긋나지 않게 합니다. 로컬 서버는 우선 루프백 주소에만 바인딩합니다.

| 환경 변수 | 위치 | 기준 또는 설정 방법 |
| --- | --- | --- |
| `APP_ENV` | 백엔드 | 로컬은 `development`. 운영 설정에서 SQLite3로 조용히 대체하지 않게 검사 |
| `DATABASE_URL` | 백엔드 | 로컬 기준 `sqlite+pysqlite:///./database/buildlog.sqlite3`. 상대 파일 경로는 반드시 프로젝트 루트 기준 절대 경로로 정규화 |
| `SECRET_KEY` | 백엔드 | Phase 1에서 무작위 생성해 실제 `.env`에만 저장. 예제·문서에는 값 없음 |
| `CORS_ORIGINS` | 백엔드 | JSON 배열 `["http://localhost:5173"]` |
| `SESSION_COOKIE_NAME` | 백엔드 | `buildlog_session` |
| `SESSION_MAX_AGE_SECONDS` | 백엔드 | 기본 28800초(8시간), 세션 서명 유효기간 기준 |
| `SESSION_COOKIE_SECURE` | 백엔드 | 로컬 HTTP에서는 false, 운영 HTTPS에서는 true |
| `VITE_API_BASE_URL` | 프론트 | `http://localhost:8000` |

설정 로더가 루트 `.env`를 명시적으로 읽도록 구현합니다. 실행 폴더가 `backend`여도 DB 파일이 `backend/database`에 잘못 만들어지지 않아야 합니다. 프론트에는 서버 비밀값, DB 비밀번호나 연결 문자열을 넣지 않습니다.

## 6. 인증과 권한의 구현 기준

새 회원 기능을 추가하지 않고, 정해진 가입·로그인·권한 규칙을 다음 방식으로 구현합니다.

- 이메일과 비밀번호 검증은 FastAPI에서 처리합니다. 비밀번호는 `pwdlib[argon2]`로 해시하여 저장합니다.
- 로그인 상태는 Starlette의 서명된 HttpOnly 세션 쿠키로 유지합니다. React의 localStorage에 인증 정보를 저장하지 않습니다.
- 쿠키에는 사용자 식별자와 CSRF 검증용 임의값 등 최소 정보만 넣습니다. 서명 쿠키는 암호화 저장소가 아니므로 비밀번호나 비공개 기록을 넣지 않습니다.
- 기본 세션 유지시간은 8시간으로 설정하고, 미들웨어의 서명 갱신·만료 동작을 로그인 테스트에 포함합니다. 만료되거나 서명이 잘못되면 다시 로그인해야 합니다.
- 요청마다 DB에서 현재 사용자를 읽어 로그인 상태와 운영자 여부를 확인합니다. 닉네임이나 권한을 쿠키 값만으로 확정하지 않습니다.
- 쿠키는 HttpOnly, SameSite=Lax로 설정하고 운영 HTTPS에서 Secure를 사용합니다.
- React API 요청은 `credentials: 'include'`를 사용합니다. FastAPI는 정확한 프론트 출처만 허용하고 자격 증명 허용을 켭니다. 출처에 `*`를 사용하지 않습니다.
- 쿠키를 사용하는 변경 요청에는 허용 Origin 검사와 세션에 연결된 CSRF 토큰 검사를 적용합니다. 로그인·가입도 다른 출처에서 요청할 수 없게 하고, 요청 위조·누락·만료를 서버 테스트로 확인합니다.
- 로그인 상태 확인과 CSRF 토큰 전달은 기존 인증을 지원하는 내부 API로 구현합니다. 소셜 로그인, 이메일 확인, 비밀번호 찾기, 별도 토큰 갱신 화면 등 새 기능은 추가하지 않습니다.
- 일반 회원가입 요청으로 운영자 권한을 지정할 수 없게 합니다. 운영자 준비는 Phase 11에서 로컬 운영 절차로 문서화합니다.

## 7. SQLite3와 Supabase PostgreSQL 확인 기준

DB가 달라도 기존 사용자 기능과 권한 결과가 같아야 합니다.

| 대상 | 구현·검증 기준 |
| --- | --- |
| DB 연결 | SQLAlchemy의 동기식 연결과 세션을 공통 사용. SQLite3와 PostgreSQL은 `DATABASE_URL`로 구분 |
| 외래키 | SQLite3의 각 새 연결에서 외래키 검사를 켜고 테스트. PostgreSQL에서도 관계 제약 확인 |
| 길이·필수값 | SQLite3의 문자열 타입 선언만 믿지 않고 API 입력과 저장 처리에서 기존 길이·공백 조건 검사 |
| 중복·연결 대상 | 이메일·닉네임·좋아요·신고의 중복과 댓글·좋아요·신고 대상 제약을 DB에서도 확인 |
| 날짜·시간 | 서버 생성 시각은 UTC 기준으로 저장·전달하고 화면은 한국 시간으로 표시. SQLite3의 시간대 정보 차이는 공통 변환으로 처리 |
| 상태 전환 | 완료·해결 시각 생성, 취소 시각 제거, 미해결로 되돌릴 때 해결 방법 보존을 두 DB에서 확인 |
| 검색·정렬 | spec에서 정한 검색 필드·포함 검색·정렬을 공통 처리. 대소문자·한글·공백·특수문자 입력에서 두 DB 결과 차이 확인 |
| DB 구조 변경 | 공통 SQLAlchemy 모델과 Alembic 이력 사용. SQLite3 변경은 필요 시 Alembic batch 방식 적용. PostgreSQL 전용 타입·함수에 의존하지 않게 설계 |
| 테스트 격리 | 로컬 자동 테스트는 별도 임시 SQLite3 DB. Supabase 검증은 운영 데이터와 분리된 환경에서 수행 |

Supabase는 우선 DB로만 사용합니다. 프로젝트와 연결 정보는 아직 제공받지 않았고, 원격 DB 연결이나 마이그레이션은 하지 않았습니다. 해당 확인은 계획대로 Phase 13에서 마칩니다.

Supabase 연결 시에는 PostgreSQL 연결 문자열과 Psycopg 드라이버를 사용하고 TLS 연결을 확인합니다. 직접 연결과 세션 풀러 중 실제 실행 환경에서 가능한 방식을 고릅니다. 마이그레이션과 검증에 사용할 연결 방식을 각각 확인하며 트랜잭션 풀러를 무조건 사용하지 않습니다.

React에서 Supabase Data API로 우회 접근하지 않으며, 사용하지 않는 DB 접근 경로를 차단하거나 필요한 RLS 정책을 적용해 비공개 기록의 노출을 막는지 검증합니다. 이 상태가 확인되기 전에는 Supabase 검증 완료로 표시하지 않습니다.

## 8. 앞으로 사용할 명령

다음 명령은 해당 Phase에서 코드·설정·의존성 파일을 준비한 뒤 사용합니다. 현재는 파일이 아직 없으므로 실행할 수 없으며 Phase 0에서 실행하지 않았습니다.

### Phase 1: 가상환경 준비와 백엔드 실행

프로젝트 루트에서 설치된 Python 3.14.6을 명시적으로 선택합니다.

```powershell
py -V:Astral/CPython3.14.6 -m venv backend/.venv
```

`backend/requirements.txt`를 준비한 뒤, `backend` 폴더에서 실행할 명령입니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

가상환경 활성화 스크립트를 실행하거나 PowerShell 실행 정책을 변경할 필요는 없습니다. 서버는 별도 터미널에서 유지합니다.

### Phase 1: 프론트엔드 실행

`frontend/package.json`과 잠금 파일을 준비한 뒤, `frontend` 폴더에서 사용할 명령입니다. 첫 의존성 설치로 잠금 파일을 만들 때는 `npm.cmd install`, 잠금 파일이 마련된 이후에는 `npm.cmd ci`를 사용합니다.

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### Phase 1 이후: 테스트·빌드

백엔드 테스트와 해당 설정이 준비된 뒤 `backend`에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

프론트 테스트 설정과 `test` 스크립트가 준비된 뒤 `frontend`에서 실행합니다.

```powershell
npm.cmd run test -- --run
npm.cmd run build
```

### Phase 2 이후: DB 준비

모델·Alembic 설정과 첫 마이그레이션을 만든 뒤 `backend`에서 실행합니다. Phase 1에서는 실행하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Supabase에 적용하기 전에는 연결 대상이 운영 DB가 아닌 검증 DB인지 확인합니다. SQLite3 검증만으로 원격 DB 검증을 대신하지 않습니다.

## 9. 기록 제외 규칙과 유지한 파일

- 기존 `.gitignore`에 `.env`, `.env.*`, `.venv`, `node_modules`, `dist`, `__pycache__`, 로그 제외와 `.env.example` 예외가 있습니다.
- SQLite3 파일과 journal·wal·shm 부속 파일, 테스트 캐시·보고서 등 개발 산출물 제외는 Phase 1에서 DB 생성 전에 보완합니다. Phase 0에서는 `.gitignore`를 바꾸지 않았습니다.
- `docs/README.md`는 내용과 SHA256 해시가 기존과 같습니다.
- Phase 0에서는 `.git`, `.env`, 가상환경, `node_modules`, `dist`, DB 파일을 만들지 않았습니다.

## 10. 다음 단계와 사용자가 준비할 내용

- Phase 0의 환경 확인과 문서 충돌 정리를 마쳤습니다. Phase 1 진행은 사용자 확인 후 별도로 수행합니다.
- 현재 추가로 설치해야 할 Python·Node.js나 사용자가 전달해야 할 계정·비밀값은 없습니다.
- Phase 1에서 프로젝트 전용 가상환경·패키지·React·FastAPI 뼈대와 설정 예제를 준비합니다. 비밀값은 그때 로컬에서 생성합니다.
- Supabase 검증 전에는 접근 가능한 별도 검증용 프로젝트와 DB 연결 설정이 필요합니다. 비밀번호와 전체 연결 문자열을 채팅에 붙여 넣을 필요는 없습니다.
- 휴대폰 실기기 확인은 이후 단계에서 같은 네트워크, PC 접속 주소, 서버 바인딩·허용 출처와 방화벽을 확인합니다.
- 아직 앱이 없으므로 화면 확인, 실제 패키지 조합 실행 테스트, 데이터 저장·권한 테스트와 Supabase 연결 검증은 수행하지 않았습니다.

## 11. 확인에 사용한 공식 자료

아래 링크와 패키지 레지스트리의 메타데이터를 확인했습니다. 검색 결과의 오래된 버전 정보와 다를 경우 조회 시점의 공식 레지스트리 정보를 사용했습니다.

- [Vite 시작 안내와 Node.js 조건](https://vite.dev/guide/)
- [FastAPI 비밀번호 해시 안내](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
- [Starlette 세션 쿠키와 CORS](https://starlette.dev/middleware/)
- [SQLAlchemy 2.1 문서](https://docs.sqlalchemy.org/en/21/intro.html)
- [Alembic SQLite3 batch 마이그레이션](https://alembic.sqlalchemy.org/en/latest/batch.html)
- [SQLite 외래키](https://www.sqlite.org/foreignkeys.html)
- [Supabase PostgreSQL 연결](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [PyPI FastAPI 배포 메타데이터](https://pypi.org/pypi/fastapi/json)
- [PyPI SQLAlchemy 배포 메타데이터](https://pypi.org/pypi/SQLAlchemy/json)
- [npm React 배포 메타데이터](https://registry.npmjs.org/react/latest)
- [npm Vite 배포 메타데이터](https://registry.npmjs.org/vite/latest)
- [npm Vitest 배포 메타데이터](https://registry.npmjs.org/vitest/latest)
