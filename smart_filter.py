#!/usr/bin/env python3
"""
Smart Drug Name Filter
識別真正的藥物名稱並過濾掉非藥物詞彙
"""

import re
from typing import Set, List

class DrugNameFilter:
    """藥物名稱智能過濾器"""

    # 已知的藥物名後綴
    DRUG_SUFFIXES = {
        # 單克隆抗體
        'mab', 'umab', 'timab', 'zumab', 'ximab',
        # 激酶抑制劑
        'inib', 'nib',
        # 其他
        'cept', 'pine', 'dine', 'xen', 'lide', 'tecan',
        'vir', 'zole', 'pril', 'sartan', 'pam', 'grel'
    }

    # 常見的非藥物詞彙（英文）
    NON_DRUG_WORDS = {
        'abstract', 'accepted', 'access', 'account', 'achieve', 'acid',
        'active', 'activity', 'acute', 'add', 'adequate', 'adjust',
        'admission', 'adopt', 'adult', 'advance', 'adverse', 'affect',
        'afford', 'age', 'agent', 'aggressive', 'agree', 'aid',
        'aim', 'alcohol', 'alert', 'algorithm', 'align', 'alive',
        'all', 'allow', 'alternative', 'always', 'amount', 'analysis',
        'analyze', 'and', 'animal', 'announce', 'annual', 'another',
        'answer', 'any', 'apparent', 'appeal', 'appear', 'applaud',
        'applicable', 'apply', 'approach', 'appropriate', 'approval',
        'approve', 'april', 'arbitrary', 'arc', 'architecture',
        'area', 'argue', 'arm', 'array', 'arrange', 'arrest',
        'arrival', 'arrive', 'arrogant', 'arrow', 'art', 'artery',
        'article', 'artificial', 'artist', 'as', 'ascend', 'ash',
        'ask', 'aspect', 'asphalt', 'aspiration', 'aspire', 'assembly',
        'assess', 'asset', 'assign', 'assignment', 'assimilate',
        'assist', 'associate', 'association', 'assort', 'assume',
        'assumption', 'assure', 'asthma', 'astonish', 'astound',
        'astray', 'astronomy', 'astronomy',
        'table', 'follow', 'result', 'method', 'study', 'patient',
        'treatment', 'therapy', 'disease', 'condition', 'symptom',
        'diagnosis', 'test', 'analysis', 'value', 'level', 'risk',
        'benefit', 'safety', 'efficacy', 'adverse', 'event', 'rate',
        'significant', 'p', 'data', 'clinical', 'trial', 'phase',
        'response', 'progression', 'survival', 'time', 'duration',
        'dose', 'regimen', 'administration', 'route', 'oral', 'iv',
        'indication', 'contraindication', 'warning', 'precaution',
        'class', 'type', 'form', 'weight', 'capacity', 'volume',
        'year', 'month', 'day', 'week', 'hour', 'minute', 'second',
        'number', 'percent', 'ratio', 'range', 'median', 'mean',
        'standard', 'deviation', 'confidence', 'interval', 'odds',
        'relative', 'absolute', 'college', 'american', 'international',
        'workshop', 'score', 'scale', 'deficiency', 'events', 'zone',
        'chromosome', 'marker', 'protein', 'myeloma', 'cancer',
        'breast', 'prostate', 'nhl', 'cll', 'aml',
    }

    def is_likely_drug_name(self, name: str) -> bool:
        """
        判斷一個名稱是否可能是藥物名

        Strategy:
        1. 清理前綴（去除數字、括號、特殊字符）
        2. 長度檢查 (4-80 字元)
        3. 排除常見非藥物詞彙和含多個詞的短語
        4. 檢查已知的藥物名後綴
        5. 檢查是否包含大寫字母 (西方藥物命名慣例)
        6. 排除明顯的非藥物模式

        Returns:
            bool: 是否可能是藥物名
        """

        # 清理前綴 - 移除前導的數字、括號、特殊符號
        name = re.sub(r'^[\(\)\[\]\{\}0-9]+', '', name).strip()

        # 長度檢查
        if len(name) < 4 or len(name) > 80:
            return False

        # 排除包含逗號、分號或括號的名稱
        if ',' in name or ';' in name or '(' in name or ')' in name:
            return False

        # 排除全大寫的短名稱（通常是縮寫或非藥物詞）
        if name.isupper() and len(name) <= 5:
            return False

        # 排除常見非藥物詞彙
        name_lower = name.lower()
        if name_lower in self.NON_DRUG_WORDS:
            return False

        # 排除包含多個空格的短語（可能是疾病名稱或其他文本）
        word_count = len(name.split())
        if word_count > 2:
            return False

        # 如果有多個詞，檢查是否任何詞是非藥物詞
        if word_count > 1:
            words = name.lower().split()
            for word in words:
                if word in self.NON_DRUG_WORDS:
                    return False

        # 排除明顯是普通英文詞的名稱（全小寫，沒有大寫字母）
        if name_lower == name and not any(suffix in name_lower for suffix in self.DRUG_SUFFIXES):
            # 例外：如果是中文或包含特殊字符，可能是藥物名
            if not re.search(r'[\u4e00-\u9fff]|-|/|\(|\)', name):
                return False

        # 檢查已知的藥物名後綴
        has_drug_suffix = any(name.lower().endswith(suffix) for suffix in self.DRUG_SUFFIXES)

        # 檢查是否包含大寫字母（西方藥物命名）
        has_capital = any(c.isupper() for c in name)

        # 檢查是否包含中文字符（中文藥物名）
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', name))

        # 檢查是否包含數字和字母的混合（通常是藥物）
        has_mixed_alphanumeric = bool(re.search(r'[a-zA-Z].*[0-9]|[0-9].*[a-zA-Z]', name))

        # 綜合判定
        if has_drug_suffix or has_chinese or has_mixed_alphanumeric:
            return True

        if has_capital and len(name) >= 6:
            return True

        return False

    def filter_drugs(self, drugs: Set[str]) -> Set[str]:
        """
        過濾藥物集合

        Returns:
            過濾後的藥物集合
        """
        return {drug for drug in drugs if self.is_likely_drug_name(drug)}


def test_filter():
    """測試過濾器"""

    filter = DrugNameFilter()

    test_cases = [
        # (name, expected_result)
        ('trastuzumab', True),        # 真實藥物名
        ('rituximab', True),          # 真實藥物名
        ('bortezomib', True),         # 真實藥物名
        ('paclitaxel', True),         # 真實藥物名
        ('Active', False),            # 非藥物詞
        ('Acute', False),             # 非藥物詞
        ('Agents', False),            # 非藥物詞
        ('CD20', True),               # 藥物靶點
        ('HER2', True),               # 藥物靶點
        ('Herceptin', True),          # 商品名
        ('Avastin', True),            # 商品名
        ('Albinism', False),          # 疾病，非藥物
        ('Alectinib', True),          # 真實藥物
        ('Afstyla', True),            # 真實藥物
        ('Adverse', False),           # 非藥物詞
        ('Assessment', False),        # 非藥物詞
    ]

    print("Testing Drug Name Filter:")
    print("=" * 60)

    for name, expected in test_cases:
        result = filter.is_likely_drug_name(name)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}: '{name}' -> {result} (expected {expected})")


def apply_filter_to_results():
    """應用過濾器到之前的結果"""

    filter = DrugNameFilter()

    # 乳癌藥物（之前提取的）
    breast_drugs = {
        'Aazathioprine', 'Abciximab', 'Abemaciclib', 'Abevmy', 'Abiraterone',
        'Abraxane', 'Actemra', 'Active', 'Activity', 'Acute', 'Adalimumab',
        'Adefovir', 'Adverse', 'Afinitor', 'Aflibercept', 'Agents',
        'Aldesleukin', 'Alectinib', 'Alirocumab', 'Alphanate',
        'trastuzumab', 'pertuzumab', 'lapatinib', 'paclitaxel', 'docetaxel',
        'doxorubicin', 'tamoxifen', 'fulvestrant', 'letrozole', 'anastrozole',
        'palbociclib', 'ribociclib'
    }

    filtered_breast = filter.filter_drugs(breast_drugs)

    print("\n" + "=" * 60)
    print("Filtered Breast Cancer Drugs:")
    print("=" * 60)
    print(f"Before: {len(breast_drugs)} drugs")
    print(f"After:  {len(filtered_breast)} drugs")
    print("\nSamples:")
    for drug in sorted(filtered_breast)[:20]:
        print(f"  ✓ {drug}")


if __name__ == '__main__':
    test_filter()
    apply_filter_to_results()
