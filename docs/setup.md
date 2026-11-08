# BuildLog 개발 환경과 실행 기준

최신 AI 확장 실행은 [자동 요약 실행 안내](materials-ai-setup.md)를 따릅니다. 현재 head는 `0003_material_analysis`이며 실제 Supabase에 적용했습니다. 아래 단계별 기록의 이전 head/미구현 표시는 해당 작업 시점의 상태입니다.

## 1. 문서 상태

- 확인일: 2026-10-22 (한국 시간)
- 현재 단계: Phase 3 — 회원가입·로그인·닉네임 변경과 권한 확인 완료
- 다음 단계: Phase 4 — 공부 기록·할 일·오류 기록 데이터 구조
- 이 문서는 Phase 0 당시의 점검과 Phase 1~3 구현 결과, 현재 실행 방법을 기록합니다. 이후 요청에 따라 실행 DB를 Supabase PostgreSQL로 전환하도록 준비했습니다. 실제 원격 연결은 아직 하지 않았습니다.
- 현재 DB 설정과 실행 절차는 [supabase.md](supabase.md)를 참고합니다. `backend/.env`에 Session pooler 정보를 입력해야 서버를 사용할 수 있습니다. 기존 SQLite3 파일과 루트 `.env`는 보존하며, 루트 `.env`는 더 이상 읽지 않습니다.
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

## 3. Phase 0 당시 컴퓨터에서 확인한 결과

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

아래는 2026-10-22에 공식 배포 정보로 확인한 버전 기준입니다. Phase 1~3 항목과 PostgreSQL 드라이버는 설치했습니다. 실제 버전은 백엔드 `requirements.txt`와 프론트엔드 `package-lock.json`을 기준으로 합니다. 드라이버 설치와 원격 연결 검증은 구분합니다.

| 역할 | 설치 후보 버전 | 준비 단계 |
| --- | --- | --- |
| API | FastAPI 0.159.1 | Phase 1 |
| 실행 서버 | Uvicorn 0.54.0 | Phase 1 |
| 입력·응답 검사 | Pydantic 2.14.1 | Phase 1 |
| 환경 설정 | pydantic-settings 2.16.1 | Phase 1 |
| DB 접근 | SQLAlchemy 2.1.6, 동기식 세션 | Phase 2 설치·테스트 완료 |
| DB 구조 변경 | Alembic 1.20.0 | Phase 2 설치・마이그레이션 완료 |
| 비밀번호 해시 | pwdlib[argon2] 0.3.1 | Phase 2 설치·테스트 완료 |
| 이메일 형식 검사 | email-validator 2.3.0 | 공통 모델 검증을 위해 Phase 2에 설치 |
| 서명 쿠키 | Starlette SessionMiddleware와 itsdangerous 2.2.0 | Phase 3 설치·테스트 완료 |
| 백엔드 테스트 | pytest 9.1.1, HTTPX2 2.16.0 | Phase 1 설치·테스트 완료 |
| 화면 | React·React DOM 19.3.1 | Phase 1 |
| 화면 이동 | react-router-dom 7.18.4 | Phase 3 설치·테스트 완료 |
| 프론트 개발·빌드 | Vite 8.3.5, @vitejs/plugin-react 6.1.2 | Phase 1 |
| 화면 테스트 | Vitest 5.0.5, @testing-library/react 16.3.3, @testing-library/dom 10.4.2, jsdom 30.1.3 | Phase 1부터 필요한 테스트에 사용 |
| PostgreSQL 연결 | psycopg[binary] 3.3.6 | 설치 완료, 실제 Supabase 연결 검증 대기 |

확인한 내용은 다음과 같습니다.

- Python 패키지의 선언된 Python 최소 버전이 선택한 Python 3.14.6을 허용합니다.
- Pydantic Core, SQLAlchemy, Argon2 바인딩 및 Psycopg Binary에서 Python 3.14 Windows 환경에 맞는 wheel 배포를 확인했습니다.
- Alembic 1.20.0은 SQLAlchemy 2.0 이상을 요구하므로 선택한 2.1.6이 조건에 맞습니다.
- React DOM의 React 요구조건과 React Testing Library의 React 19 지원 범위를 확인했습니다.
- Vite, React 플러그인, Vitest와 jsdom의 Node.js 요구조건이 현재 Node.js 24.22.0을 허용합니다. React 플러그인과 Vitest의 Vite 요구조건도 확인했습니다.
- FastAPI 0.159.1, Starlette 1.9.0, Pydantic 2.14.1의 실제 조합으로 API 테스트를 통과했습니다. Starlette의 기존 HTTPX 사용 중단 안내에 따라 HTTPX2 2.16.0을 사용하고 경고를 해소했습니다.

Phase 1 항목은 설치·API 테스트·화면 테스트·빌드·Chrome 연결 검증을 마쳤습니다. Phase 2는 설치·SQLite3 마이그레이션·사용자 모델 테스트를 마쳤습니다. 이후 후보의 메타데이터 확인은 실제 설치·연결 검증과 구분합니다.

## 5. 개발 주소와 환경 변수

| 구분 | 기준 |
| --- | --- |
| React 화면 | `http://localhost:5173` |
| FastAPI 서버 | `http://localhost:8000` |
| API 경로 | 기능 API는 `/api` 아래에 연결 예정 |
| 상태 확인 | Phase 1에서 `/api/health` 제공 예정 |
| 실행 DB | Supabase PostgreSQL, Session pooler 포트 `5432` |
| 기존 DB 파일 | `database/buildlog.sqlite3` 보존. 현재 실행에 사용하지 않음 |
| 자동 테스트 DB | pytest가 만든 임시 폴더의 별도 SQLite3 DB |
| 백엔드 설정 파일 | `backend/.env`, 항목 공유는 `backend/.env.example` |
| 프론트 설정 파일 | `frontend/.env`, 항목 공유는 `frontend/.env.example` |

프론트와 API 주소의 호스트 표기는 `localhost`로 통일합니다. `localhost`와 `127.0.0.1`을 섞어 쿠키와 허용 출처가 어긋나지 않게 합니다. 로컬 서버는 우선 루프백 주소에만 바인딩합니다.

| 환경 변수 | 위치 | 기준 또는 설정 방법 |
| --- | --- | --- |
| `APP_ENV` | 백엔드 | 로컬은 `development`. SQLite3는 명시적인 `test` 환경에서만 허용 |
| `DATABASE_URL` | 백엔드 | 필수. Session pooler의 PostgreSQL URI. 포트 `5432`, DB 비밀번호의 특수문자 URL 인코딩, `sslmode=require`. 누락·오류 시 SQLite3 대체 없음 |
| `SECRET_KEY` | 백엔드 | Phase 1에서 무작위 생성해 실제 `.env`에만 저장. 예제·문서에는 값 없음 |
| `CORS_ORIGINS` | 백엔드 | JSON 배열 `["http://localhost:5173"]` |
| `SESSION_COOKIE_NAME` | 백엔드 | `buildlog_session` |
| `SESSION_MAX_AGE_SECONDS` | 백엔드 | 기본 28800초(8시간), 세션 서명 유효기간 기준 |
| `SESSION_COOKIE_SECURE` | 백엔드 | 로컬 HTTP에서는 false, 운영 HTTPS에서는 true |
| `VITE_API_BASE_URL` | 프론트 | `http://localhost:8000` |

설정 로더는 실행 폴더와 관계없이 `backend/.env`를 읽습니다. 루트 `.env`는 읽지 않습니다. 프론트에는 서버 비밀값, DB 비밀번호나 연결 문자열을 넣지 않습니다. 테스트에서만 명시적으로 지정한 SQLite3 경로를 사용합니다.

## 6. 인증과 권한의 구현 기준

다음은 구현한 회원과 인증 기준입니다. Phase 1의 API 통신, Phase 2의 사용자 모델과 해시 위에 Phase 3의 가입·로그인·닉네임 변경 API, 세션 인증과 CSRF 검사를 연결했습니다.

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

### 현재 사용할 수 있는 회원 화면과 API

| 화면 | 주소 | 동작 |
| --- | --- | --- |
| 회원가입 | `http://localhost:5173/signup` | 이메일·닉네임·비밀번호 입력. 성공하면 로그인으로 이동 |
| 로그인 | `http://localhost:5173/login` | 이메일로 로그인. 성공하면 홈으로 이동 |
| 내 기록 홈 | `http://localhost:5173/` | 로그인한 사용자의 현재 닉네임 표시. 기록 기능은 이후 Phase에서 추가 |
| 계정 설정 | `http://localhost:5173/settings` | 본인 닉네임 변경 |

| API | 역할 |
| --- | --- |
| `GET /api/accounts/session` | 현재 사용자 또는 익명 상태와 CSRF 값 조회. 응답은 캐시하지 않음 |
| `POST /api/accounts/signup` | 일반 사용자 생성. 성공해도 자동 로그인하지 않음 |
| `POST /api/accounts/login` | 로그인하고 세션·CSRF 값 교체 |
| `GET /api/accounts/me` | 인증된 본인 정보 조회 |
| `PATCH /api/accounts/me` | 인증된 본인 닉네임 변경. 다른 사용자 ID 입력은 허용하지 않음 |

브라우저는 필요한 쿠키와 Origin을 자동 전달합니다. API를 직접 호출한다면 세션 조회로 받은 쿠키를 유지하고, 모든 변경 요청에 허용 Origin과 세션의 CSRF 값을 보내야 합니다. 실제 쿠키·CSRF 값과 비밀번호를 문서나 명령 기록에 남기지 않습니다.

가입·로그인 실패 시 비밀번호는 비우고 나머지 입력을 유지합니다. 닉네임 실패 시 새 입력과 저장된 이름을 유지합니다. 입력 검사·DB 실패 응답에는 비밀번호, DB 매개변수나 원본 검증 입력을 포함하지 않습니다.

세션은 사용자 ID를 저장하고 현재 이메일·닉네임은 DB에서 읽습니다. 공개 기록과 댓글이 추가되면 같은 사용자 관계에서 현재 닉네임을 읽도록 연결합니다. 아직 없는 공개 화면의 동작을 확인한 것으로 표시하지 않습니다.

서버를 시작하기 전에 새 환경이라면 먼저 Alembic 마이그레이션을 적용합니다. 서버 시작이나 요청이 사용자 테이블을 자동 생성하지는 않습니다.

## 7. SQLite3와 Supabase PostgreSQL 확인 기준

DB가 달라도 기존 사용자 기능과 권한 결과가 같아야 합니다. Phase 2에서 사용자 모델과 로컬 SQLite3 연결을 구현하고 검증했고, 현재는 PostgreSQL 실행 설정으로 바꿨습니다. 기록·댓글·좋아요·신고 모델과 실제 PostgreSQL 연결은 아직 구현·검증하지 않았습니다.

| 대상 | 구현·검증 기준 |
| --- | --- |
| DB 연결 | SQLAlchemy 동기식 세션과 Psycopg. 실행은 PostgreSQL 필수, SQLite3는 격리 테스트 전용 |
| 외래키 | SQLite3의 각 새 연결에서 외래키 검사를 켜고 테스트. PostgreSQL에서도 관계 제약 확인 |
| 길이·필수값 | SQLite3의 문자열 타입 선언만 믿지 않고 API 입력과 저장 처리에서 기존 길이·공백 조건 검사 |
| 중복·연결 대상 | 이메일·닉네임·좋아요·신고의 중복과 댓글·좋아요·신고 대상 제약을 DB에서도 확인 |
| 날짜·시간 | 서버 생성 시각은 UTC 기준으로 저장·전달하고 화면은 한국 시간으로 표시. SQLite3의 시간대 정보 차이는 공통 변환으로 처리 |
| 상태 전환 | 완료·해결 시각 생성, 취소 시각 제거, 미해결로 되돌릴 때 해결 방법 보존을 두 DB에서 확인 |
| 검색·정렬 | spec에서 정한 검색 필드·포함 검색·정렬을 공통 처리. 대소문자·한글·공백·특수문자 입력에서 두 DB 결과 차이 확인 |
| DB 구조 변경 | 공통 SQLAlchemy 모델과 Alembic 이력 사용. SQLite3 변경은 필요 시 Alembic batch 방식 적용. PostgreSQL 전용 타입·함수에 의존하지 않게 설계 |
| 테스트 격리 | 로컬 자동 테스트는 별도 임시 SQLite3 DB. Supabase 검증은 운영 데이터와 분리된 환경에서 수행 |

Supabase는 DB로만 사용합니다. 연결 정보는 아직 입력되지 않았고, 원격 DB 연결이나 마이그레이션은 하지 않았습니다. 사용자 입력 후 우선 회원 기능을 확인하며, 전체 기능의 최종 검증은 Phase 13에서 마칩니다.

Supabase 연결은 사용자가 선택한 Session pooler 포트 `5432`로 통일합니다. PostgreSQL 연결 문자열과 Psycopg 드라이버를 사용하고 SSL을 요구합니다. 마이그레이션도 같은 설정을 사용합니다.

React에서 Supabase Data API로 우회 접근하지 않으며, 사용하지 않는 DB 접근 경로를 차단하거나 필요한 RLS 정책을 적용해 비공개 기록의 노출을 막는지 검증합니다. 이 상태가 확인되기 전에는 Supabase 검증 완료로 표시하지 않습니다.

## 8. 설치와 실행 방법

서버·화면·테스트·의존성 파일과 가상환경은 준비되어 있습니다. 개발 서버는 각각 별도 터미널에서 실행합니다. 현재 `backend/.env`에는 기존 서버 비밀값을 유지했으며 **DATABASE_URL을 사용자가 입력해야 합니다**. [Supabase 준비 절차](supabase.md)에 따라 먼저 테이블을 준비합니다.

다른 환경에서 처음 준비할 때만 아래 명령을 프로젝트 루트에서 실행합니다. `backend/.env.example`을 바탕으로 로컬 설정을 만들고 무작위 비밀값을 파일에만 저장합니다. 기존 비밀값이 있으면 유지합니다. 그 뒤 DATABASE_URL을 직접 입력합니다.

```powershell
py -V:Astral/CPython3.14.6 -c "from pathlib import Path; import secrets; p=Path('backend/.env'); text=p.read_text(encoding='utf-8') if p.exists() else Path('backend/.env.example').read_text(encoding='utf-8'); p.write_text(text.replace('SECRET_KEY=\n', 'SECRET_KEY='+secrets.token_urlsafe(48)+'\n'), encoding='utf-8')"
```

### Phase 1: 가상환경 준비와 백엔드 실행

프로젝트 루트에서 설치된 Python 3.14.6을 명시적으로 선택합니다.

```powershell
py -V:Astral/CPython3.14.6 -m venv backend/.venv
```

`backend` 폴더에서 실행합니다. 현재 작업 환경에는 설치되어 있으며, 새 환경에서 의존성을 복원할 때 첫 줄을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

가상환경 활성화 스크립트를 실행하거나 PowerShell 실행 정책을 변경할 필요는 없습니다. 서버는 별도 터미널에서 유지합니다.

### Phase 1: 프론트엔드 실행

`frontend` 폴더에서 실행합니다. 잠금 파일이 준비되어 있으므로 새 환경에서 설치할 때는 `npm.cmd ci`를 사용합니다. 현재 작업 환경에는 이미 설치되어 있습니다.

```powershell
npm.cmd ci
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

### Phase 1 이후: 테스트·빌드

`backend`에서 실행합니다. 테스트는 실행 중인 서버나 개발용 비밀값·DB에 의존하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

`frontend`에서 실행합니다.

```powershell
npm.cmd run test -- --run
npm.cmd run build
```

### Phase 2 이후: DB 준비

사용자 모델·Alembic 설정과 첫 마이그레이션은 준비되어 있습니다. 과거 로컬 SQLite3에는 적용했지만 Supabase에는 아직 적용하지 않았습니다. `backend/.env`에 Session pooler 연결 정보를 입력한 뒤 `backend`에서 실행합니다. 이 명령은 아직 적용하지 않은 변경만 적용합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

적용 상태와 모델·DB 구조의 일치 여부를 확인할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
```

적용 성공 뒤 예상 버전은 `0001_users (head)`입니다. Supabase에서의 실제 적용 상태는 아직 확인하지 않았습니다. 서버 시작이나 상태 확인 API 호출만으로 테이블을 자동 생성하지 않습니다. DB 구조는 Alembic으로 관리합니다.

개발 DB에는 테스트 계정을 넣지 않았습니다. 자동 테스트는 매번 별도 임시 SQLite3 DB에 마이그레이션을 적용하며, 실제 `.env`의 DB에 연결하지 않습니다.

사용자 생성 로직은 `app/accounts/services.py`에 있습니다. 일반 계정만 생성하며 호출자가 트랜잭션을 완료하도록 commit하지 않고 flush까지만 수행합니다. 이메일은 공백 제거 후 소문자로 통일하고, 닉네임은 공백 제거 후 허용 문자와 길이를 검사합니다. Phase 3의 회원가입 API가 이 로직을 사용합니다.

Supabase에 적용하기 전에는 연결 대상이 운영 DB가 아닌 검증 DB인지 확인합니다. SQLite3 검증만으로 원격 DB 검증을 대신하지 않습니다.

## 9. 기록 제외 규칙과 유지한 파일

- 기존 `.gitignore`에 `.env`, `.env.*`, `.venv`, `node_modules`, `dist`, `__pycache__`, 로그 제외와 `.env.example` 예외가 있습니다.
- SQLite3 파일과 journal·wal·shm 부속 파일, 테스트 캐시·보고서 제외는 Git 준비 작업에서 보완되었고 Phase 1에서 실제 적용을 확인했습니다. 이번 Phase에서는 `.gitignore`를 추가 변경하지 않았습니다.
- `docs/README.md`는 내용과 SHA256 해시가 기존과 같습니다.
- Phase 0에서는 `.git`, `.env`, 가상환경, `node_modules`, `dist`, DB 파일을 만들지 않았습니다.

## 10. 다음 단계와 사용자가 준비할 내용

- Phase 3을 완료했습니다. 다음 기능 단계는 Phase 4의 세 종류 기록 데이터 구조입니다. 이번에는 요청에 따라 PostgreSQL 전환 준비만 했습니다.
- 사용자가 `backend/.env`의 DATABASE_URL에 Supabase Session pooler 정보를 입력하고 Alembic을 적용한 뒤 가입·로그인을 확인해야 합니다. Python·Node.js 추가 설치는 필요하지 않습니다. 비밀값은 채팅으로 전달하지 않습니다.
- 프로젝트 전용 가상환경·패키지·React·FastAPI 뼈대와 설정 예제를 준비했습니다. 비밀값은 로컬 `.env`에만 생성했습니다.
- Supabase 검증 전에는 접근 가능한 별도 검증용 프로젝트와 DB 연결 설정이 필요합니다. 비밀번호와 전체 연결 문자열을 채팅에 붙여 넣을 필요는 없습니다.
- 휴대폰 실기기 확인은 이후 단계에서 같은 네트워크, PC 접속 주소, 서버 바인딩·허용 출처와 방화벽을 확인합니다.
- Phase 1 확인 완료: 당시 백엔드 테스트 8개, 화면 테스트 3개, 프론트 빌드와 Chrome 1440px·360px 화면·API 연결. 이번 Phase 2에서는 프론트를 변경하지 않아 해당 검사를 반복하지 않았습니다.
- Phase 2 확인 완료: 기존 테스트를 포함한 백엔드 테스트 43개, `pip check`, 실제 로컬 DB의 `0001_users` 적용과 `alembic check`. 중복·필수값·길이·해시·평문 저장 차단·외래키·마이그레이션·새 프로세스에서 데이터 유지 검사를 포함합니다.
- Phase 3 확인 완료: 백엔드 테스트 총 80개, 화면·API 요청 테스트 21개, 프론트 빌드와 `pip check`. 실제 Chrome에서 임시 DB로 가입·로그인·닉네임 변경·재접속, 실패 시 입력 처리, 익명 접근 제한, 쿠키 보호와 1440px·360px 레이아웃을 확인했습니다.
- Phase 3에서는 기존 SQLite3 스키마와 개발 데이터를 유지했습니다. QA용 계정은 별도 임시 DB에만 저장했습니다. Windows에서 인코딩된 드라이브 문자가 포함된 DB URL도 같은 파일을 가리키도록 검사합니다.
- 미확인: Edge·Safari·실제 휴대폰, 공개 기록·댓글의 닉네임 반영, 실제 Supabase PostgreSQL 연결. PostgreSQL용 테이블 정의의 오프라인 생성만 확인했습니다.
- PostgreSQL 전환 준비 확인: 백엔드 테스트 90개와 `pip check` 통과. 설정 누락 시 중단, PostgreSQL 마이그레이션 SQL의 오프라인 생성, 연결 오류의 정보 비노출과 임시 SQLite3 회원 API 회귀 테스트를 확인했습니다. 실제 원격 접속·테이블 생성은 하지 않았으며, 기존 SQLite3 파일의 작업 전후 SHA256이 같습니다.
- README.md와 기존 AGENTS.md를 유지했고 commit·push는 하지 않았습니다. 검증용 개발 서버는 확인 후 종료합니다. 직접 화면을 보려면 위의 두 서버 실행 명령을 사용합니다.

## 별도 예시 대시보드 — /dashboard

Figma의 `Dashboard · Desktop · 1440` 화면을 별도 React 페이지로 추가했습니다. 2026-10-24부터 기존 로그인 세션을 연결했으므로 `/dashboard`도 로그인이 필요합니다. 인사말·왼쪽 계정명·아바타 첫 글자는 실제 로그인한 사용자의 닉네임으로 표시하고, 공부 기록·할 일 등은 예시로 유지합니다. 기존 홈·가입·로그인·계정 설정 화면은 그대로 사용합니다.

`frontend` 폴더에서 실행합니다. 이미 개발 서버가 실행 중이면 다시 켤 필요 없이 아래 주소를 열면 됩니다.

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

브라우저 주소: `http://localhost:5173/dashboard`. 처음에는 `http://localhost:5173/login`에서 로그인하세요. 로그인 성공 후에는 기존 홈(`/`)으로 이동하므로 주소창에서 `/dashboard`를 열면 됩니다. 실제 사용에는 기존 FastAPI·DB 연결과 회원 테이블 준비가 필요합니다. 백엔드 실행·DB 준비 명령은 위의 설치·실행 절차와 [supabase.md](supabase.md)를 참고합니다.

- 공부 기록 24개, 남은 할 일 4개, 미해결 오류 2개와 완료 8/12개(67%)는 Figma의 예시 데이터입니다. 날짜·최근 공부 기록도 예시를 유지합니다. 닉네임만 로그인한 사용자의 실제 정보입니다.
- 로그인 상태를 읽는 동안은 로딩 안내가 표시됩니다. 비로그인이 확인되면 `/login`으로 이동하고, 연결 실패 시에는 오류와 다시 연결 버튼을 표시합니다. 오류를 예시 이름이나 비로그인 상태로 바꾸지 않습니다.
- 계정 설정에서 닉네임 변경 후 브라우저 뒤로 가기로 대시보드에 돌아오면 변경된 이름이 반영됩니다. 새로고침하면 기존 세션 API에서 현재 이름을 다시 읽습니다. 다른 탭의 변경·세션 만료를 실시간 감지하는 기능은 추가하지 않았습니다.
- 할 일 체크와 해제는 현재 화면 안에서만 반영되며 남은 개수·완료율도 함께 바뀝니다. 새로고침하면 원래 예시 상태로 돌아옵니다.
- 로고는 기존 홈(`/`), 대시보드 메뉴는 `/dashboard`, 계정 설정은 기존 `/settings`에 연결합니다. 홈·계정 설정·대시보드는 같은 로그인 상태를 공유하며 기존 접근 보호를 사용합니다.
- 아직 없는 기록·할 일·공개 기록 경로와 작성·전체 보기·할 일 관리 버튼은 연결하지 않고 비활성 상태로 표시합니다. 예시 공부 기록도 실제 DB 연결 결과를 뜻하지 않습니다.
- CSS Modules로 스타일을 분리했습니다. Figma 화면 전체를 이미지로 넣지 않고 React 요소와 CSS로 구성했습니다. 새 패키지는 설치하지 않았습니다.

현재 확인 결과: 프론트엔드 테스트 36개와 빌드 통과. 모의 API를 사용한 실제 Chrome에서 1440px·360px 너비의 2자·20자 닉네임, 계정 설정 변경 후 복귀, 실제 새로고침과 예시 체크 초기화, 비로그인 접근, 연결 오류·재시도를 확인했습니다. 대시보드 자체의 추가 회원 조회와 할 일 저장 요청은 없었습니다. 실제 Supabase와 로그인 계정을 연결한 수동 확인, 다른 브라우저와 실제 휴대폰은 이번 작업에서 수행하지 않았습니다.

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

## 학습 자료함 M2: 테이블 준비

학습 자료함 메타정보 모델과 Alembic `0002_materials`를 추가했습니다. 현재 실행 DB는 기존과 같이 Supabase PostgreSQL이고, 새 자료 API·파일 저장·업로드 화면 연결은 아직 없습니다.

적용은 기존 `backend/.env`를 준비한 뒤 **backend 폴더**에서 수행합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

적용 후 revision은 `0002_materials`입니다. 반복 upgrade는 재적용되지 않습니다. 이번 M2 작업에서는 원격 DB 적용을 수행하지 않았습니다. 적용 전 백업과 검증용 DB, Supabase RLS·접근 역할 확인은 [supabase.md 8절](supabase.md#8-학습-자료함-m2-테이블-적용-안내)을 따릅니다. 사용자 DB의 downgrade는 새 자료 메타정보를 지우므로 실행하지 않습니다.

백엔드 자동 테스트는 기존처럼 `backend`에서 `.\.venv\Scripts\python.exe -m pytest -q`로 실행합니다. 테스트는 별도 임시 SQLite를 사용하며 개발용 uploads나 실제 Supabase 데이터를 사용하지 않습니다.

## 학습 자료함 M3: 업로드 API

- `POST /api/materials`: 기존 로그인 쿠키·Origin·X-CSRF-Token을 사용해 multipart의 title, 선택 memo, file 한 개를 보냅니다. FastAPI `/docs`에도 입력 필드를 표시합니다. CSRF 값이나 쿠키를 복사해 공유하지 않습니다.
- 서버의 `.venv`에 python-multipart 0.0.32와 Pillow 13.0.0을 설치했습니다. 다른 환경에서는 기존 `backend` 폴더에서 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`로 준비합니다.
- 자료 테이블 적용은 여전히 기존 `alembic upgrade head` 명령으로 별도 수행해야 합니다. 이번 M3 작업에서 실제 Supabase 적용이나 저장을 확인하지 않았습니다.
- 최종 원본은 `backend/uploads/{작성자ID}/{UUID}.{확장자}`, 앱 임시 파일은 `backend/uploads/.tmp`입니다. 시작 폴더와 무관한 경로를 사용합니다. 이 폴더 전체는 Git에서 제외되며 공개 URL로 제공하지 않습니다.
- 폴더에 쓰기 권한과 충분한 디스크 공간이 필요합니다. 저장소와 Supabase 메타정보를 함께 백업해야 합니다. 준비된 디렉터리에는 실제 자료를 넣지 않았습니다.
- 이미지 최대 5MiB, MP4 최대 30MiB를 검사합니다. multipart 오버헤드를 포함한 요청 전체는 32MiB, 수신 시간은 120초로 제한합니다. 이미지 디코딩은 Pillow, MP4는 컨테이너 구조·브랜드·영상 트랙 검사입니다. MP4 재생 가능 코덱을 모두 보증하지 않습니다.
- 프론트의 업로드 버튼은 아직 비활성입니다. 화면 연결은 M5, 목록·원본·삭제 API는 M4에서 진행합니다. 기존 실행 서버가 `--reload`가 아니라면 코드를 반영하려면 서버를 다시 시작해야 합니다.
- 처리 중 강제 종료나 DB 커밋 결과 불확실, 정리 오류 로그가 생기면 신규 업로드를 멈추고 uploads의 UUID 파일과 materials의 stored_filename을 내부에서 대조합니다. `.tmp` 파일은 활성 업로드가 없는지 먼저 확인하고, 행이 있는 원본을 지우지 않습니다. DB와 파일 복구는 백업을 기준으로 하며 자동 정리 서비스는 아직 없습니다.

구현 시 [Starlette 파일·폼 처리 안내](https://www.starlette.io/requests/)와 [Pillow 이미지 처리 안내](https://pillow.readthedocs.io/en/stable/handbook/security.html)를 참고했습니다.

## 학습 자료함 M4: 목록·원본 보기·삭제 API

| API | 동작 |
| --- | --- |
| GET /api/materials | 로그인한 본인 자료 목록 JSON. 등록일·ID 역순 |
| GET /api/materials/{id}/file | 로그인한 본인 원본. 전체 200, 범위 요청 206 |
| DELETE /api/materials/{id} | 본인 자료 삭제. 기존 Origin·X-CSRF-Token 필요, 성공 204 |

- 기존 쿠키 로그인을 재사용합니다. 없는 자료·다른 사람 자료는 동일한 404이고, 운영자도 작성자 조건을 우회하지 않습니다. 본인 원본만 없는 경우 원본 보기는 404이며 행 삭제는 가능합니다.
- 원본 응답에 private/no-store, nosniff, 검증된 MIME과 안전하게 인코딩한 원래 파일명을 사용합니다. 범위 밖 요청은 416, 잘못된 Range 문법은 400입니다. 모든 요청에서 인증을 검사합니다.
- 삭제는 파일을 `backend/uploads/.trash/{임시UUID}-{저장용파일명}`으로 옮긴 후 DB 행 삭제를 커밋합니다. 실패하면 롤백·원본 복원을 시도합니다. DB 삭제 후 내부 파일 제거만 실패하면 API 성공은 유지하고 정리 필요 로그를 남깁니다.
- 복원도 실패하면 .trash에 바이트를 보존합니다. 자동으로 다른 파일을 덮어쓰지 않습니다. 정리/복구 로그 발생 시 활성 업로드·원본 열기를 중지한 다음, DB의 소유자·stored_filename과 .trash 이름 뒷부분을 대조해 백업을 기준으로 복구합니다. 행이 없는 파일인지, 원본이 이미 복구됐는지 먼저 확인해야 합니다.
- 현재 프론트는 여전히 예시 목록이며 실제 API를 부르지 않습니다. M5에서 화면 연결을 진행합니다. 실제 Supabase 적용·데이터 검증·MP4 브라우저 재생은 아직 확인하지 않았습니다.

## 학습 자료함 M5: 화면에서 실제 자료 사용

`/materials`는 이제 실제 업로드·목록·원본 보기·삭제 API를 호출합니다. 예시 목록은 제거했으며 DB 오류를 예시 데이터로 대체하지 않습니다. AI는 연결 예정입니다.

1. **backend** 폴더에서 기존 `.env` 설정을 유지하고 테이블 적용 상태를 확인합니다. `alembic current`가 `0002_materials`인지 확인하고 필요하면 upgrade를 실행합니다. 실제 DB에 명령을 실행하는 작업이며 이번 M5 자동 검증에서는 원격 DB에 적용하지 않았습니다.

   ```powershell
   .\.venv\Scripts\python.exe -m alembic current
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

2. **frontend** 폴더의 별도 터미널에서 실행합니다. 이미 같은 서버가 실행 중이면 다시 실행하지 않고 새로고침합니다.

   ```powershell
   npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
   ```

3. `http://localhost:5173/login`에서 기존 계정으로 로그인하고 홈의 학습 자료함 링크 또는 `http://localhost:5173/materials`를 엽니다.
4. 제목과 선택 메모, PNG/JPG 최대 5MiB 또는 MP4 최대 30MiB 파일 한 개를 선택해 업로드합니다. 저장 성공 후 목록과 필터·개수, 새로고침 후 유지를 확인합니다.
5. 원본 보기를 누르면 로그인 쿠키로 받은 원본을 같은 화면에 표시합니다. 원본 닫기와 내려받기가 가능하며, 영상은 사용자가 재생합니다. 이 방식은 전체 파일을 최대 30MiB까지 받아 Blob으로 여는 방식입니다. 서버의 Range API는 별도로 유지됩니다.
6. 삭제 확인을 취소하면 유지되고, 확인 후 서버 성공을 받으면 목록에서 제거됩니다. 실패하면 카드를 유지합니다. 연결/시간 초과로 결과가 불확실하면 ‘목록 새로 확인’ 후 재시도하여 중복 등록을 피합니다.
7. 목록이 계속 실패하면 백엔드 실행, DB 연결과 테이블 적용 상태, CORS 출처를 확인합니다. 계정·쿠키·CSRF·DB 비밀값을 로그나 답변에 복사하지 않습니다.

화면 구현의 자동 검증은 테스트 80개·빌드 통과입니다. Chrome 1440px/360px에서 별도 임시 서버·SQLite·uploads로 실제 가입/로그인/PNG·MP4 업로드/원본 재생/새로고침/삭제를 검증했습니다. 검증 서버는 종료했으며 프로젝트의 실제 Supabase 저장·권한, 다른 브라우저·휴대폰 검증은 남아 있습니다.
