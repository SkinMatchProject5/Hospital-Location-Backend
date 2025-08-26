#!/usr/bin/env python3
"""
Hospital-Location-Backend 시작 스크립트
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("🏥 Hospital-Location-Backend 시작")
    print(f"   포트: {settings.PORT}")
    print(f"   디버그 모드: {settings.DEBUG}")
    print(f"   로그 레벨: {settings.LOG_LEVEL}")
    print("=" * 50)
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
