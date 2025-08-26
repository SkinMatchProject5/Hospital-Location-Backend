# 🔧 환경 설정 가이드

## .env 파일 생성 방법

### 1. 환경 파일 복사
```bash
# Hospital-Location-Backend 디렉토리에서
copy env_template.txt .env
```

또는 파일 탐색기에서:
1. `env_template.txt` 파일을 복사
2. 이름을 `.env`로 변경

### 2. 필수 환경변수 설정

`.env` 파일을 열어서 다음 값들을 실제 값으로 변경하세요:

```bash
# OpenAI API 키 (필수)
OPENAI_API_KEY=sk-your-actual-openai-api-key-here

# Qdrant 벡터 데이터베이스 설정 (선택사항)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-qdrant-api-key-here
```

### 3. 최소 설정으로 테스트

Qdrant 없이도 기본 기능은 테스트할 수 있습니다:

```bash
# .env 파일에서 최소한 이것만 설정
OPENAI_API_KEY=sk-your-actual-api-key
DEBUG=true
PORT=8002
```

### 4. 설정 확인

```bash
python manual_test.py
```

## 📝 참고사항

- **OpenAI API 키**는 필수입니다 (임베딩 생성용)
- **Qdrant**는 실제 검색에 필요하지만 기본 테스트는 가능합니다
- **DEBUG=true**로 설정하면 자세한 로그를 볼 수 있습니다
- **PORT=8002**는 AI-Analysis-Backend와 연동을 위한 기본 포트입니다
