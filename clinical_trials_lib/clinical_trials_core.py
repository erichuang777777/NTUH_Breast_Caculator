#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
臨床試驗核心分析引擎 - 無依賴版本（適合 Flask 應用）
Clinical Trials Analysis Core Engine
"""

import requests
from typing import List, Dict, Tuple
from abc import ABC, abstractmethod


class SpecialtyAnalyzer(ABC):
    """科室分析的基礎類別"""
    
    def __init__(self, location: str = "Taiwan"):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        self.location = location
        self.specialty_name = ""
    
    @abstractmethod
    def get_importance_score(self, trial: Dict) -> Tuple[int, List[str]]:
        """計算試驗的重要程度分數"""
        pass
    
    def extract_trial_info(self, study: Dict) -> Dict:
        """提取試驗關鍵信息"""
        protocol = study.get('protocolSection', {})
        id_module = protocol.get('identificationModule', {})
        status_module = protocol.get('statusModule', {})
        contact_module = protocol.get('contactsLocationsModule', {})
        sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
        design_module = protocol.get('designModule', {})
        
        # 提取地點
        locations = contact_module.get('locations', [])
        trial_locations = {}
        for loc in locations:
            country = loc.get('country', '')
            city = loc.get('city', '')
            if country and city:
                if country not in trial_locations:
                    trial_locations[country] = []
                if city not in trial_locations[country]:
                    trial_locations[country].append(city)
        
        # 提取聯絡信息
        central_contacts = contact_module.get('centralContacts', [])
        contact_info = None
        if central_contacts:
            contact = central_contacts[0]
            contact_info = {
                'name': contact.get('name', ''),
                'phone': contact.get('phone', ''),
                'email': contact.get('email', '')
            }
        
        phases = design_module.get('phases', [])
        status = status_module.get('overallStatus', 'UNKNOWN')
        recruitment_status = status_module.get('recruitmentStatus', 'UNKNOWN')
        has_results = study.get('hasResults', False)
        results_first_post_date = status_module.get('resultsFirstPostDate', '')
        enrollment = design_module.get('enrollmentInfo', {}).get('count', 0)
        
        return {
            'nct_id': id_module.get('nctId', ''),
            'title': id_module.get('officialTitle', ''),
            'status': status,
            'recruitment_status': recruitment_status,
            'phases': phases,
            'locations': trial_locations,
            'num_countries': len(trial_locations),
            'num_sites': sum(len(cities) for cities in trial_locations.values()),
            'sponsor': sponsor_module.get('leadSponsor', {}).get('name', ''),
            'contact_info': contact_info,
            'has_results': has_results,
            'results_date': results_first_post_date,
            'enrollment': enrollment
        }
    
    def fetch_trials(self, condition: str, location: str = None, pageSize: int = 100) -> List[Dict]:
        """從 API 獲取試驗數據"""
        if location is None:
            location = self.location
        
        params = {
            'query.cond': condition,
            'query.locn': location,
            'pageSize': pageSize
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            studies = data.get('studies', [])
            return studies
        
        except requests.RequestException as e:
            print(f"API 請求失敗: {str(e)}")
            return []


class BreastCancerAnalyzer(SpecialtyAnalyzer):
    """乳癌臨床試驗分析"""
    
    def __init__(self, location: str = "Taiwan"):
        super().__init__(location)
        self.specialty_name = "乳癌"
    
    def get_importance_score(self, trial: Dict) -> Tuple[int, List[str]]:
        """計算乳癌試驗重要程度"""
        score = 0
        reasons = []
        
        if 'PHASE3' in trial['phases']:
            score += 30
            reasons.append("✅ Phase 3 (關鍵性試驗)")
        
        if trial['num_countries'] >= 10:
            score += 20
            reasons.append(f"🌍 全球試驗 ({trial['num_countries']} 個國家)")
        elif trial['num_countries'] >= 5:
            reasons.append(f"🌍 多國試驗 ({trial['num_countries']} 個國家)")
        
        if trial['num_sites'] >= 20:
            score += 15
            reasons.append(f"📍 大規模 ({trial['num_sites']} 個地點)")
        
        if trial['has_results']:
            score += 20
            reasons.append("📄 已發布結果")
        
        if trial['recruitment_status'] == 'RECRUITING':
            score += 15
            reasons.append("✅ 正在招募")
        elif trial['status'] == 'COMPLETED':
            score += 5
            reasons.append("✅ 已完成並發表")
        
        return min(score, 100), reasons


class HematologyAnalyzer(SpecialtyAnalyzer):
    """血液科/血液腫瘤臨床試驗分析"""
    
    def __init__(self, location: str = "Taiwan"):
        super().__init__(location)
        self.specialty_name = "血液科"
    
    def get_importance_score(self, trial: Dict) -> Tuple[int, List[str]]:
        """計算血液科試驗重要程度"""
        score = 0
        reasons = []
        
        if 'PHASE3' in trial['phases']:
            score += 30
            reasons.append("✅ Phase 3 (關鍵性試驗)")
        elif 'PHASE2' in trial['phases']:
            score += 10
            reasons.append("⚠️ Phase 2 (臨床評估階段)")
        
        if trial['num_countries'] >= 10:
            score += 20
            reasons.append(f"🌍 全球試驗 ({trial['num_countries']} 個國家)")
        elif trial['num_countries'] >= 5:
            score += 12
            reasons.append(f"🌍 多國試驗 ({trial['num_countries']} 個國家)")
        
        if trial['enrollment'] >= 500:
            score += 15
            reasons.append(f"📊 大規模 ({trial['enrollment']} 人入組)")
        elif trial['enrollment'] >= 200:
            score += 10
            reasons.append(f"📊 中等規模 ({trial['enrollment']} 人入組)")
        
        if trial['has_results']:
            score += 20
            reasons.append("📄 已發布結果")
        
        if trial['recruitment_status'] == 'RECRUITING':
            score += 15
            reasons.append("✅ 正在招募")
        
        return min(score, 100), reasons
