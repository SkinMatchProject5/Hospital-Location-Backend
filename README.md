# 🏥 Hospital-Location-Backend

AI 진단 결과 기반 병원 검색 시스템

## 📋 개요

이 프로젝트는 AI 분석 백엔드에서 전송되는 XML 진단명을 받아 임베딩 기반 하이브리드 검색을 수행하여 관련 병원 정보를 반환하는 백엔드 서비스입니다.

## 🏗️ 아키텍처

```
AI-Analysis-Backend → Hospital-Location-Backend → Frontend
                     (XML 진단명)              (병원 정보)
```

### 주요 기능
- ✅ XML 진단명 파싱
- ✅ 임베딩 기반 벡터 검색 (OpenAI text-embedding-3-small)
- ✅ 코사인 유사도 + BM25 하이브리드 검색
- ✅ Qdrant 벡터 데이터베이스 연동
- ✅ 병원 정보 반환 (name, tell, addr, url)

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 1. 저장소 클론 및 디렉토리 이동
cd Hospital-Location-Backend

# 2. 환경변수 파일 생성
cp .env.example .env

# 3. .env 파일에 실제 값 입력
# - OPENAI_API_KEY: OpenAI API 키
# - QDRANT_URL: Qdrant 서버 URL
# - QDRANT_API_KEY: Qdrant API 키
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
# 개발 모드
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002

# 또는 직접 실행
python app/main.py
```

## 📡 API 엔드포인트

### POST `/api/v1/search/search-ft-xml`

AI 분석 백엔드에서 전송된 XML 진단명을 기반으로 병원 검색

**요청 예시:**
```json
{
  "xml": "<root><label id_code=\"0\" score=\"85.0\">광선각화증</label><summary>자외선 노출이 많은 부위인 얼굴에 붉은색의 각질성 반점이 관찰됩니다.</summary></root>",
  "top_k": 24,
  "final_k": 2,
  "rerank_mode": "ce"
}
```

**응답 예시:**
```json
{
  "results": [
    {
      "name": "서울대학교병원 피부과",
      "tell": "02-2072-2114",
      "addr": "서울특별시 종로구 대학로 101",
      "url": "https://www.snuh.org",
      "score": 0.89
    }
  ],
  "meta": {
    "embedding_model": "text-embedding-3-small",
    "search_strategy": "hybrid_cosine_bm25"
  },
  "total_count": 1,
  "search_time_ms": 245.6
}
```

### GET `/health`

서비스 헬스 체크

## 🔧 설정

주요 환경변수:

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 키 | 필수 |
| `QDRANT_URL` | Qdrant 서버 URL | 필수 |
| `QDRANT_API_KEY` | Qdrant API 키 | 선택 |
| `DEFAULT_TOP_K` | 초기 후보 검색 개수 | 24 |
| `DEFAULT_FINAL_K` | 최종 결과 반환 개수 | 2 |
| `BM25_WEIGHT` | BM25 가중치 | 0.5 |
| `PORT` | 서버 포트 | 8002 |

## 📊 성능 목표

- **평균 응답 시간**: ≤ 900ms
- **P95 응답 시간**: ≤ 1200ms
- **동시 요청 처리**: 100개
- **타임아웃**: 30초

## 📁 프로젝트 구조

```
Hospital-Location-Backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 애플리케이션
│   ├── core/
│   │   ├── config.py          # 설정 관리
│   │   └── logging.py         # 로깅 설정
│   ├── api/
│   │   └── search.py          # 검색 API 엔드포인트
│   ├── models/
│   │   ├── requests.py        # 요청 모델
│   │   ├── responses.py       # 응답 모델
│   │   └── diagnosis.py       # 진단 정보 모델
│   └── services/
│       └── search_service.py  # 검색 서비스 (구현 예정)
├── .env.example               # 환경변수 템플릿
├── requirements.txt           # 패키지 의존성
└── README.md                  # 프로젝트 문서
```

## 🧪 테스트

```bash
# 헬스 체크
curl http://localhost:8002/health

# 검색 API 테스트
curl -X POST http://localhost:8002/api/v1/search/search-ft-xml \
  -H "Content-Type: application/json" \
  -d '{"xml": "<root><label id_code=\"0\" score=\"85.0\">광선각화증</label></root>"}'
```

## 📝 다음 단계

- [ ] XML 파싱 서비스 구현
- [ ] 임베딩 서비스 구현  
- [ ] Qdrant 연동 서비스 구현
- [ ] 하이브리드 검색 엔진 구현
- [ ] AI-Analysis-Backend와의 통합 테스트
