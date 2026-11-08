# Supabase PostgreSQL 연결과 실행

최신 확인(2026-10-25): 기존 연결로 `0003_material_analysis` 적용과 요약 컬럼·materials RLS 활성화를 확인했습니다. 기존 테이블·데이터를 삭제하지 않았습니다. [AI 요약 실행 안내](materials-ai-setup.md)의 `backend/run.py`로 DB 준비와 서버 시작을 함께 수행할 수 있습니다. 아래 M2 기록은 당시 상태이며 실제 유료 AI 호출과 Data API 역할별 접근 검증은 별도입니다.

## 1. 이번에 준비한 내용

- FastAPI와 Alembic은 `backend/.env`를 읽습니다. 실행하는 폴더가 바뀌어도 같습니다.
- 프로젝트 루트의 기존 `.env`는 보존했지만 더 이상 읽지 않습니다. 터미널에 같은 이름의 환경 변수가 있으면 파일보다 우선하므로 예전 `DATABASE_URL`이 남아 있지 않은지도 확인합니다. 값을 출력할 필요는 없습니다.
- 실행 DB는 PostgreSQL입니다. 설정이 없거나 틀리면 중단하며 SQLite로 자동 연결하지 않습니다.
- SQLAlchemy와 Psycopg 3.3.6을 사용합니다. 연결은 SSL을 요구하고, 연결 대기는 기본 10초로 제한합니다. 사용 전 연결 상태도 검사합니다.
- 회원 테이블과 이메일·닉네임 중복 검사, 비밀번호 해시, 로그인·본인 정보·닉네임 변경 API는 유지했습니다.
- 현재 마이그레이션은 `0001_users` 하나입니다. `users`와 변경 이력용 `alembic_version` 테이블을 준비합니다. 공부·할 일·오류 기록 기능과 테이블은 아직 구현 전이며 이번에 추가하지 않았습니다.
- 기존 `database/buildlog.sqlite3`와 데이터는 보존합니다. 이번에 Supabase로 옮기지 않으며, Supabase에는 새 회원부터 저장합니다.

## 2. backend/.env 입력

현재 프로젝트에는 `backend/.env`를 준비했습니다. 기존 서버의 `SECRET_KEY`는 유지했으며 `DATABASE_URL`은 비워 두었습니다. 이 파일의 **DATABASE_URL 항목만** 채우면 됩니다.

새 환경에서는 `backend/.env.example`을 `backend/.env`로 복사하고, 32자 이상의 무작위 `SECRET_KEY`도 준비해야 합니다. 예제에는 실제 비밀값이 없습니다.

Supabase 프로젝트에서 **Connect → Session pooler → URI** 연결 정보를 확인합니다. 연결 URI의 비밀번호 자리에 해당 프로젝트의 **DB 비밀번호**를 넣어 `DATABASE_URL`에 저장합니다. 비밀번호에 `@`, `:`, `/`, `#`, `%` 같은 특수문자가 있으면 URI에 넣는 비밀번호 부분을 URL 인코딩해야 합니다. 기존 `%` 인코딩을 두 번 인코딩하지 않습니다.

| 확인할 값 | 입력 기준 |
| --- | --- |
| Host | Session pooler 화면의 호스트. 보통 `.pooler.supabase.com`으로 끝남 |
| Port | `5432`. Transaction pooler의 `6543`은 사용하지 않음 |
| Database | 화면에 표시된 DB 이름. 일반적으로 `postgres` |
| User | 화면의 전체 사용자 이름. 일반적으로 `postgres.` 뒤에 프로젝트 식별자가 붙음 |
| Password | Supabase 프로젝트의 DB 비밀번호. 계정 로그인 비밀번호나 API 키가 아님 |
| SSL | URI 끝에 `?sslmode=require`. 이미 다른 옵션이 있으면 `&sslmode=require` |

URI의 시작은 `postgresql://` 또는 `postgresql+psycopg://`를 사용합니다. 내부에서 Psycopg 드라이버로 연결합니다. 전체 연결 문자열을 답변, 터미널 출력, Git 또는 프론트 설정에 넣지 않습니다.

`APP_ENV=development`, 로컬 HTTP의 `SESSION_COOKIE_SECURE=false`, `CORS_ORIGINS=["http://localhost:5173"]` 등 나머지 개발 설정은 이미 준비했습니다. `SECRET_KEY`는 비우거나 새로 덮어쓰지 않습니다. 인터넷 운영 HTTPS로 배포할 때는 별도 운영 설정이 필요합니다.

## 3. 명령 하나로 테이블 준비

**DB 연결 정보를 입력한 다음**, VS Code 터미널에서 프로젝트의 `backend` 폴더로 이동해 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Alembic은 DB의 `alembic_version`으로 적용한 변경을 기억합니다. 같은 명령을 다시 실행해도 이미 적용한 변경을 중복 적용하지 않습니다. 기존 마이그레이션의 회원 테이블 구조는 바꾸지 않았습니다. 서버 시작 시 자동으로 테이블을 만들지는 않습니다.

적용 뒤 버전을 확인하려면 같은 폴더에서 다음 명령을 사용할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m alembic current
```

성공 시 현재 버전은 `0001_users (head)`입니다. **지금은 연결 정보가 없어 Supabase에서 이 결과를 확인하지 않았습니다.** 이미 같은 이름의 테이블을 별도로 만들어 둔 DB라면 충돌할 수 있습니다. 테이블 삭제나 강제 이력 지정으로 우회하지 말고 기존 구조부터 확인합니다.

## 4. 서버와 화면 실행

DB 준비가 성공한 뒤, 기존 백엔드 서버가 실행 중이면 해당 터미널에서 `Ctrl+C`로 종료하고 **backend**에서 다시 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

다른 VS Code 터미널의 **frontend** 폴더에서 실행합니다.

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

현재 컴퓨터에는 필요한 패키지를 설치했습니다. 다른 컴퓨터에서는 먼저 `backend`에서 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`, `frontend`에서 `npm.cmd ci`로 설치합니다. 가상환경을 새로 만드는 절차는 [setup.md](setup.md)를 참고합니다.

## 5. 회원가입과 로그인으로 확인

1. 브라우저에서 `http://localhost:5173/signup`을 엽니다.
2. 새 이메일·닉네임·비밀번호로 가입합니다. 성공하면 로그인 화면으로 이동합니다.
3. `http://localhost:5173/login`에서 방금 가입한 계정으로 로그인합니다.
4. 홈에서 본인 닉네임이 보이는지 확인하고, 계정 설정에서 닉네임 변경과 새로고침 후 유지 여부를 확인합니다.
5. 필요하면 로그인한 같은 브라우저에서 `http://localhost:8000/api/accounts/me`를 열어 본인 정보가 조회되는지 확인합니다. 쿠키나 비밀번호를 공유하지 않습니다.
6. Supabase Table Editor의 `users`에서 새 회원이 저장됐는지 확인할 수 있습니다. `password_hash`를 포함한 행 전체를 복사하거나 공유하지 않습니다.

기존 SQLite 계정은 이전하지 않았으므로 새 DB에서는 다시 가입해야 합니다. `/api/health`의 성공은 서버 실행만 확인하며 DB 연결 성공을 뜻하지 않습니다.

## 6. 실행에 실패하면 확인할 것

| 상황 | 확인할 내용 |
| --- | --- |
| `Invalid backend/.env` 또는 설정 오류 | 파일 위치와 `DATABASE_URL` 입력 여부, URI 형식, Session pooler 포트 `5432`, SSL, 기존 `SECRET_KEY`와 CORS JSON 형식 |
| DB 연결 또는 마이그레이션 실패 | Pooler의 Host·User·Database가 정확한지, DB 비밀번호와 URL 인코딩이 맞는지, 프로젝트가 활성 상태인지, 네트워크·접근 제한·DB 권한이 허용되는지 |
| 가입·로그인에서 `503` | 서버 설정과 DB 연결을 확인하고 Alembic 명령이 성공했는지 확인. 서버는 상세 DB 오류나 연결 문자열을 응답에 담지 않음 |
| 기존 계정으로 로그인 실패 | SQLite 데이터는 옮기지 않았으므로 새 DB에 가입했는지 확인 |
| 가입·로그인에서 `403` 또는 쿠키 문제 | 브라우저 주소를 `localhost`로 통일하고 CORS 출처·로컬 HTTP의 Secure 쿠키 설정을 확인 |
| 이메일·닉네임 중복 `409` | 새 DB에서 이미 사용한 이메일·닉네임인지 확인 |

오류가 나도 SQLite로 우회하지 않습니다. 설정을 수정한 뒤 서버를 재시작하고 Alembic 명령을 다시 실행합니다. 비밀번호나 전체 URI를 출력하지 말고, 오류 종류와 비밀값을 지운 안내만 공유하세요.

## 7. 확인한 것과 남은 일

- 완료: PostgreSQL 드라이버 설치, 패키지 의존성 검사, 백엔드 자동 테스트 90개. PostgreSQL용 마이그레이션 SQL의 오프라인 생성, SSL·연결 옵션, 설정 누락 차단과 오류의 연결 정보 비노출을 검사했습니다. 임시 SQLite에서 회원 API와 마이그레이션 재실행도 검사했습니다.
- 보존 확인: 기존 SQLite 파일의 SHA256이 작업 전후 같습니다. `.env`는 Git 제외 대상이고 `.env.example`은 기록할 수 있습니다.
- 미확인: 실제 Supabase 접속·테이블 생성·PostgreSQL에서 가입 및 로그인. 사용자가 DB 정보를 입력한 뒤 위 절차로 확인해야 합니다. 기존 화면은 수정하지 않았으며 이번에 브라우저 검사를 반복하지 않았습니다.
- 다음 할 일: DB 연결 정보 입력 → Alembic 적용 → 서버 재시작 → 새 계정 가입·로그인. 기능 개발의 다음 단계는 기존 계획대로 Phase 4입니다.

연결 방식은 [Supabase PostgreSQL 연결 공식 안내](https://supabase.com/docs/guides/database/connecting-to-postgres)를, 설치 방식은 [Psycopg 공식 안내](https://www.psycopg.org/psycopg3/docs/basic/install.html)를 확인했습니다.

## 8. 학습 자료함 M2 테이블 적용 안내

`0002_materials` 마이그레이션을 준비했습니다. 기존 `0001_users` 다음에 실행되며 users 테이블·회원 데이터를 변경하지 않습니다. 이번 작업에서는 실제 Supabase에 접속하거나 적용하지 않았습니다.

적용할 DB가 맞는지 먼저 확인하고, 기존 DB 백업과 별도 검증용 DB를 준비합니다. 연결 정보는 기존 `backend/.env`를 사용하며 전체 URI를 출력하거나 공유하지 않습니다. **backend 폴더**에서 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
```

적용 후 current는 `0002_materials`를 가리켜야 합니다. 이미 적용한 DB에서 같은 upgrade 명령을 실행하면 다시 생성하지 않습니다. 서버 재시작만으로 테이블이 생성되지는 않습니다. 사용자 DB에서 downgrade를 실행하지 마세요. 새 테이블과 그 안의 메타정보가 삭제됩니다.

### 생성되는 구조

- `materials`: 작성자 users 외래키, 제목·선택 메모, 원래 파일명·고유 저장용 파일명, 종류·MIME·바이트 수, 시간대가 있는 등록일.
- 제목 1~100자·앞뒤 공백, 메모 최대 1,000자, 종류/MIME 조합, 이미지 5MiB·영상 30MiB 제한을 DB 제약으로 검사합니다. 상세한 유니코드 공백 정리는 모델에서도 검사합니다.
- `(owner_id, created_at, id)` 인덱스와 저장용 파일명 고유 제약이 생깁니다. 자료를 가진 회원을 삭제해 메타정보가 고아가 되도록 cascade를 추가하지 않았습니다.
- 파일 저장 폴더와 API는 M3 이후에 만들 예정입니다. 현재 명령은 테이블 준비만 합니다.

### Supabase 직접 접근과 역할 확인

- PostgreSQL 마이그레이션은 materials의 RLS를 활성화하고 PUBLIC 및 존재하는 anon/authenticated 역할의 테이블·ID 시퀀스 권한을 제거합니다. 공개 접근 정책은 만들지 않습니다. 기존 users의 권한·정책은 바꾸지 않습니다.
- 기존 로그인은 FastAPI 쿠키 방식입니다. Supabase Auth의 `auth.uid()`가 현재 로그인 작성자를 나타낸다고 가정하지 않습니다. 본인 자료 조회 조건은 M3/M4 API에서 `CurrentUser`로 적용합니다.
- 마이그레이션과 FastAPI는 같은 신뢰할 수 있는 백엔드 DB 역할을 사용하는 구성을 기준으로 합니다. 테이블 소유자는 일반적으로 RLS를 우회하므로 이 역할의 접속 정보는 백엔드에만 둡니다. 별도의 제한된 런타임 역할을 쓴다면 권한/RLS 설계를 먼저 확인해야 하며, 공개 역할에 권한이나 허용 정책을 추가해 오류를 우회하지 않습니다.
- 검증용 Supabase에서 적용 후 Table Editor의 materials RLS 활성화와 정책 없음, 테이블 소유자, anon/authenticated 권한을 확인합니다. anon 및 authenticated Data API 요청으로 목록·원본 메타정보를 읽거나 삽입·수정·삭제할 수 없어야 합니다. 키를 답변·로그에 출력하지 말고 요청 결과만 확인합니다. 서비스 역할 키는 프론트에서 사용하지 않습니다.
- 실제 PostgreSQL의 권한, 역할 상속, Data API 노출·접근 차단은 아직 확인하지 않았습니다. 오프라인 SQL 생성 검사는 실제 서버 적용 성공이나 RLS 동작 검증을 대신하지 않습니다.

### M2 확인 결과

임시 SQLite에서 신규 테이블·제약·인덱스·외래키·중복 저장명, 반복 upgrade와 테스트 DB의 down/up, 기존 회원 데이터 보존을 확인했습니다. 실제 DB 연결을 차단한 테스트에서 PostgreSQL DDL·RLS/권한 제한 SQL 생성을 확인했습니다. 실제 Supabase 적용, 역할별 접근 차단과 자료 API는 아직 미확인/미구현입니다.
