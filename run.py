#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NHI 藥品計算 + 臨床試驗分析 - 啟動腳本
"""

import sys
import os
from pathlib import Path

# 添加 app 目錄到 Python 路徑
sys.path.insert(0, str(Path(__file__).parent / 'app'))
sys.path.insert(0, str(Path(__file__).parent / 'clinical_trials_lib'))

if __name__ == '__main__':
    from app import app
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║     NHI 藥品計算 + 臨床試驗分析平台                           ║
    ║     Clinical Trials Analysis Platform                          ║
    ╚════════════════════════════════════════════════════════════════╝
    
    🚀 啟動應用程式...
    
    📍 訪問地址: http://localhost:5000
    
    功能特點:
    ✅ 乳癌臨床試驗分析
    ✅ 血液科臨床試驗分析
    ✅ 患者版和醫師版統一視圖
    ✅ 實時試驗重要程度評分
    ✅ 台灣招募地點過濾
    
    按 Ctrl+C 停止應用程式
    
    """)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n✅ 應用程式已停止")
        sys.exit(0)
