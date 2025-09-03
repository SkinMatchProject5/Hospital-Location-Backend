# Hospital-Location-Backend

AI 분석 결과(FT XML/진단 텍스트)를 입력으로 받아 한국 병원 검색·랭킹을 수행하는 FastAPI 백엔드입니다. RAG 파이프라인(Qdrant + 리랭커/에이전트)으로 후보 병원을 선별합니다.

## 요구사항
- Python 3.12+
- pip / virtualenv (또는 Docker)

## 빠른 시작
- 로컬 실행
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
```
- Docker
```bash
docker build -t skinmatch/hospital-backend:latest .
docker run -p 8002:8002 skinmatch/hospital-backend:latest
# 또는
docker compose up -d
```

## 환경 변수(예시)
- PORT=8002, LOG_LEVEL=info
- Qdrant/리랭커 관련 설정은 `utils/*` 및 `pipeline/*` 내 설정/코드 참고

## API 개요
- Base URL: `http://localhost:8002`
- 문서: `/docs`, `/redoc` (main.py에 따라 설정 가능)

- Health
  - GET `/health`: 파이프라인 상태/업타임/성능 메타 반환

- Search
  - POST `/search-ft-xml`: FT XML을 입력으로 병원 후보 검색
    - Body: `{ xml: string, rerank_mode: 'llm'|'ce'|'off', top_k?: number, group_size?: number, final_k?: number }`
    - Response: `{ results: Array<object>, meta: object }`

## 디렉터리 구조
- `main.py`: FastAPI 진입점, 파이프라인 초기화/헬스/검색 API
- `pipeline/*`: RAG 파이프라인 구현
- `utils/*`: XML 파서, 로거/성능 모니터, 파이프라인 팩토리
- `models/*`: 쿼리 빌더 등
- `logs/*`: 실행 로그/요청 기록(jsonl)

