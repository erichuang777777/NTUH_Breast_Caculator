#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NHI 藥品計算 + 臨床試驗分析 - 整合 Web 應用
Flask Application for NHI Drug Calculator + Clinical Trials Analysis
"""

from flask import Flask, render_template, jsonify, request
import sys
import os
from pathlib import Path

# 添加臨床試驗模塊到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'clinical_trials_lib'))

from clinical_trials_core import BreastCancerAnalyzer, HematologyAnalyzer
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 初始化分析器
breast_analyzer = BreastCancerAnalyzer()
hematology_analyzer = HematologyAnalyzer()

# 全局數據緩存
trials_cache = {
    'breast': None,
    'hematology': None
}


@app.route('/')
def index():
    """主頁"""
    return render_template('index.html')


@app.route('/api/trials/<specialty>', methods=['GET'])
def get_trials(specialty):
    """獲取試驗數據 API"""
    location = request.args.get('location', 'Taiwan')
    force_refresh = request.args.get('refresh', 'false').lower() == 'true'
    
    # 選擇分析器
    if specialty == 'breast':
        analyzer = breast_analyzer
        condition = "breast cancer"
    elif specialty == 'hematology':
        analyzer = hematology_analyzer
        condition = "lymphoma OR leukemia OR myeloma OR anemia"
    else:
        return jsonify({'error': '不支持的科室'}), 400
    
    # 檢查緩存
    if not force_refresh and trials_cache.get(specialty):
        trials = trials_cache[specialty]
    else:
        # 從 API 獲取
        try:
            raw_trials = analyzer.fetch_trials(condition, location)
            if not raw_trials:
                return jsonify({'error': '無法獲取試驗數據'}), 500
            
            # 提取信息
            trials = []
            for study in raw_trials:
                info = analyzer.extract_trial_info(study)
                # 計算評分
                score, reasons = analyzer.get_importance_score(info)
                info['score'] = score
                info['score_reasons'] = reasons
                trials.append(info)
            
            # 排序
            trials.sort(key=lambda x: x['score'], reverse=True)
            
            # 緩存
            trials_cache[specialty] = trials
            
        except Exception as e:
            return jsonify({'error': f'獲取數據失敗: {str(e)}'}), 500
    
    # 返回數據
    return jsonify({
        'specialty': specialty,
        'location': location,
        'total_count': len(trials),
        'trials': trials,
        'statistics': get_statistics(trials)
    })


def get_statistics(trials):
    """計算試驗統計信息"""
    return {
        'phase1': sum(1 for t in trials if 'PHASE1' in t['phases']),
        'phase2': sum(1 for t in trials if 'PHASE2' in t['phases']),
        'phase3': sum(1 for t in trials if 'PHASE3' in t['phases']),
        'with_results': sum(1 for t in trials if t['has_results']),
        'terminated': sum(1 for t in trials if t['status'] == 'TERMINATED'),
        'recruiting': sum(1 for t in trials if t['recruitment_status'] == 'RECRUITING')
    }


@app.route('/api/patient-view/<specialty>')
def patient_view(specialty):
    """患者版視圖 API"""
    location = request.args.get('location', 'Taiwan')
    
    # 獲取試驗數據
    response = get_trials(specialty)
    if response[1] != 200:
        return response
    
    data = response[0].get_json() if hasattr(response, 'get_json') else response
    trials = data.get('trials', [])
    
    # 過濾：只顯示正在招募中且在指定位置的
    patient_trials = [
        t for t in trials
        if t['recruitment_status'] == 'RECRUITING' and location in t['locations']
    ]
    
    # 限制顯示數量
    patient_trials = patient_trials[:20]
    
    return jsonify({
        'view_type': 'patient',
        'specialty': specialty,
        'location': location,
        'recruiting_count': len(patient_trials),
        'trials': patient_trials
    })


@app.route('/api/doctor-view/<specialty>')
def doctor_view(specialty):
    """醫師版視圖 API"""
    location = request.args.get('location', 'Taiwan')
    
    # 獲取所有試驗
    response = get_trials(specialty)
    if response[1] != 200:
        return response
    
    data = response[0].get_json() if hasattr(response, 'get_json') else response
    trials = data.get('trials', [])
    
    # 返回前 10 個最重要的
    doctor_trials = trials[:10]
    
    return jsonify({
        'view_type': 'doctor',
        'specialty': specialty,
        'location': location,
        'top_trials': len(doctor_trials),
        'trials': doctor_trials,
        'statistics': get_statistics(trials)
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'supported_specialties': ['breast', 'hematology']
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端點不存在'}), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': '伺服器錯誤'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
