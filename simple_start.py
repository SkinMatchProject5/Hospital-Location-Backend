#!/usr/bin/env python3
"""
간단한 서버 시작 스크립트 - 오류 디버깅용
"""

def main():
    try:
        print("🔧 모듈 로드 테스트...")
        
        # 1. 설정 로드
        from app.core.config import settings
        print(f"✅ 설정: 포트 {settings.PORT}")
        
        # 2. FastAPI 앱 로드
        from app.main import app
        print("✅ FastAPI 앱 로드 성공")
        
        # 3. 기본 라우트 확인
        print(f"✅ 등록된 라우트: {len(app.routes)}개")
        
        # 4. uvicorn으로 시작
        import uvicorn
        print("🚀 서버 시작...")
        
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",  # localhost만 바인딩
            port=8002,
            reload=False,  # 리로드 비활성화
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
