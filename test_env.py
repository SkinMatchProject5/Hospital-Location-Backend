#!/usr/bin/env python3
"""환경변수 로딩 테스트"""

import os
from pathlib import Path
from dotenv import load_dotenv

print("🔍 환경변수 로딩 테스트")
print("="*50)

# 현재 작업 디렉토리
print(f"현재 작업 디렉토리: {os.getcwd()}")

# .env 파일 경로 확인
env_path = Path(__file__).parent / ".env"
print(f".env 파일 경로: {env_path}")
print(f".env 파일 존재: {env_path.exists()}")

if env_path.exists():
    print(f".env 파일 크기: {env_path.stat().st_size} bytes")

# .env 파일 로드
success = load_dotenv(env_path)
print(f"dotenv 로딩 성공: {success}")

print("\n📋 중요 환경변수들:")
print(f"QDRANT_URL: '{os.getenv('QDRANT_URL', 'NOT_SET')}'")
print(f"QDRANT_API_KEY: '{os.getenv('QDRANT_API_KEY', 'NOT_SET')[:20]}...'")
print(f"CHILDREN_COLLECTION: '{os.getenv('CHILDREN_COLLECTION', 'NOT_SET')}'")
print(f"PARENTS_COLLECTION: '{os.getenv('PARENTS_COLLECTION', 'NOT_SET')}'")
print(f"OPENAI_API_KEY: '{os.getenv('OPENAI_API_KEY', 'NOT_SET')[:20]}...'")

print("\n✅ 환경변수 로딩 테스트 완료")
