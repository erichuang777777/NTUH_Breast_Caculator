#!/usr/bin/env python3
"""
產生 PREDICT 驗證用的 ~150 個代表性 test case。
輸出純輸入資料 (predict_cases.json)，不含答案。
答案需由 R script (run_predict_R.R) 產生 → predict_snapshot.json

Usage:
    python tests/generate_predict_cases.py
"""
import json
import itertools
from pathlib import Path

OUT = Path(__file__).parent / 'predict_cases.json'

# 代表性輸入空間（謹慎選取，覆蓋常見臨床情境）
ages = [30, 40, 50, 60, 70, 80]                  # 6 ages spanning 30-80
sizes_mm = [10, 20, 30, 50]                      # T1c, T2 small, T2 large, T3
nodes = [0, 1, 3, 8]                             # N0, N1 small, N1 large, N2-3
grades = [1, 2, 3]                               # G1/G2/G3
modes = ['symp']                                  # 95% are symptomatic
er_states = ['pos', 'neg']
her2_states = ['pos', 'neg']
ki67_states = ['neg']

# Treatment combinations to test
treatments = [
    {'endo': 0, 'chemo': 0, 'trast': 0, 'bis': 0, 'name': 'no_tx'},
    {'endo': 5, 'chemo': 0, 'trast': 0, 'bis': 0, 'name': 'endo_5y'},
    {'endo': 5, 'chemo': 3, 'trast': 0, 'bis': 0, 'name': 'endo_chemo3'},
    {'endo': 5, 'chemo': 3, 'trast': 1, 'bis': 0, 'name': 'all'},
]

cases = []
case_id = 0
for age, size, n, g, mode, er, her2, ki67 in itertools.product(
        ages, sizes_mm, nodes, grades, modes, er_states, her2_states, ki67_states):
    for tx in treatments:
        # Endocrine only meaningful for ER+
        if tx['endo'] > 0 and er != 'pos':
            continue
        # Trastuzumab only for HER2+
        if tx['trast'] == 1 and her2 != 'pos':
            continue
        case_id += 1
        cases.append({
            'id': case_id,
            'age': age, 'size': size, 'nodes': n, 'grade': g,
            'mode': mode, 'er': er, 'her2': her2, 'ki67': ki67,
            'tx_endo': tx['endo'], 'tx_chemo': tx['chemo'],
            'tx_trast': tx['trast'], 'tx_bis': tx['bis'],
            'tx_name': tx['name'],
        })

# Edge cases
edge_cases = [
    {'age': 30, 'size': 50, 'nodes': 4, 'grade': 3, 'mode': 'symp',
     'er': 'neg', 'her2': 'neg', 'ki67': 'pos',
     'tx_endo': 0, 'tx_chemo': 3, 'tx_trast': 0, 'tx_bis': 0, 'tx_name': 'tnbc_aggressive'},
    {'age': 80, 'size': 10, 'nodes': 0, 'grade': 1, 'mode': 'symp',
     'er': 'pos', 'her2': 'neg', 'ki67': 'neg',
     'tx_endo': 5, 'tx_chemo': 0, 'tx_trast': 0, 'tx_bis': 0, 'tx_name': 'elderly_low_risk'},
    {'age': 55, 'size': 25, 'nodes': 1, 'grade': 2, 'mode': 'symp',
     'er': 'pos', 'her2': 'pos', 'ki67': 'pos',
     'tx_endo': 5, 'tx_chemo': 3, 'tx_trast': 1, 'tx_bis': 0, 'tx_name': 'her2_pos_full'},
]
for ec in edge_cases:
    case_id += 1
    ec['id'] = case_id
    cases.append(ec)

output = {
    'description': 'PREDICT v2.1 validation test cases',
    'generated_by': 'tests/generate_predict_cases.py',
    'count': len(cases),
    'note': 'Expected outputs to be populated by R nhs.predict via tests/run_predict_R.R',
    'cases': cases,
}

OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'OK: {len(cases)} cases -> {OUT}')
