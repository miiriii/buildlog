from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="독립 오류 확인 실습")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5176"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"message": "실습 서버 실행 중"}