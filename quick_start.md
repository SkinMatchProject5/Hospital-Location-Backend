# 🏥 Hospital-Location-Backend 빠른 시작 가이드

## 📋 현재 상태
✅ **프로젝트 구조 완성**  
✅ **핵심 서비스 구현 완료**  
✅ **API 엔드포인트 준비**  
✅ **하이브리드 검색 엔진 구현**  

## 🚀 빠른 실행 방법

### 1단계: 의존성 설치
```bash
cd Hospital-Location-Backend
pip install -r requirements.txt
```

### 2단계: 환경 설정
```bash
# .env 파일 생성 (이미 생성됨)
# 다음 값들을 실제 값으로 수정하세요:
# - OPENAI_API_KEY=실제_OpenAI_API_키
# - QDRANT_URL=실제_Qdrant_URL
# - QDRANT_API_KEY=실제_Qdrant_API_키
```

### 3단계: 기본 테스트
```bash
python manual_test.py
```

### 4단계: 서버 시작
```bash
python start.py
```

### 5단계: API 테스트
브라우저에서 다음 URL 접속:
- 헬스 체크: http://localhost:8002/health
- API 문서: http://localhost:8002/docs
- OpenAPI 스펙: http://localhost:8002/openapi.json

## 🧪 테스트 시나리오

### 기본 동작 테스트
```bash
curl -X POST "http://localhost:8002/api/v1/search/search-ft-xml" \
  -H "Content-Type: application/json" \
  -d '{
    "xml": "<root><label id_code=\"0\" score=\"85.0\">광선각화증</label><summary>자외선 노출 부위 각질성 반점</summary></root>",
    "top_k": 10,
    "final_k": 2
  }'
```

### AI-Analysis-Backend 연동
1. AI-Analysis-Backend 실행 (포트 8001)
2. Hospital-Location-Backend 실행 (포트 8002) 
3. AI 진단 요청 시 자동으로 병원 검색 실행됨

## 📊 프로젝트 구조
```
Hospital-Location-Backend/
├── app/
│   ├── main.py                 # FastAPI 애플리케이션
│   ├── core/
│   │   ├── config.py          # 환경 설정
│   │   └── logging.py         # 로깅 설정
│   ├── api/
│   │   └── search.py          # 검색 API
│   ├── models/
│   │   ├── requests.py        # 요청 모델
│   │   ├── responses.py       # 응답 모델
│   │   └── diagnosis.py       # 진단 모델
│   └── services/
│       ├── xml_parser.py      # XML 파싱
│       ├── embedding_service.py # 임베딩 생성
│       ├── qdrant_service.py  # 벡터 DB
│       ├── hybrid_search.py   # 하이브리드 검색
│       └── search_service.py  # 통합 검색
├── .env                       # 환경 변수
├── requirements.txt           # 패키지 의존성
└── start.py                  # 서버 시작 스크립트
```

## 🔧 주요 기능

### ✅ XML 진단명 파싱
- AI-Analysis-Backend XML 형식 지원
- BeautifulSoup 기반 관대한 파싱
- 진단명, 점수, 요약, 유사질병 추출

### ✅ 하이브리드 검색
- **코사인 유사도**: OpenAI 임베딩 기반 의미 검색
- **BM25**: 키워드 기반 텍스트 매칭
- **가중치 결합**: 최적 검색 결과 제공

### ✅ 응답 형식
프론트엔드 요구 형식으로 병원 정보 제공:
- `name`: 병원명
- `tell`: 전화번호  
- `addr`: 주소
- `url`: 웹사이트 URL

## ⚠️ 주의사항

1. **환경 변수**: .env 파일에 실제 API 키 필요
2. **벡터 DB**: Qdrant 연결이 필요한 완전한 검색
3. **Python 버전**: Python 3.8+ 권장
4. **포트**: 8002번 포트 사용 (AI 백엔드는 8001)

## 🚀 성공 확인 방법

1. `python manual_test.py` → 모든 테스트 통과
2. `python start.py` → 서버 정상 시작
3. http://localhost:8002/health → "healthy" 응답
4. http://localhost:8002/docs → Swagger UI 정상 표시

## 🔗 AI-Analysis-Backend 연동

AI-Analysis-Backend의 `HOSPITAL_BACKEND_URL` 설정이 이미 준비되어 있습니다:
```python
HOSPITAL_BACKEND_URL = "http://localhost:8002"
```

진단 요청 시 자동으로 병원 검색이 백그라운드에서 실행됩니다!
