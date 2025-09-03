#!/usr/bin/env python3
"""포트 8003에서 테스트 서버 시작"""

import uvicorn
from app.main import app

if __name__ == "__main__":
    print("🚀 테스트 서버 시작 (포트 8003)")
    uvicorn.run(
        app, 
        host="127.0.0.1", 
        port=8003,
        log_level="info"
    )
