#!/usr/bin/env python3
"""
匯入台大醫院藥物價格 (2024/12/5) 並建立 drug_formulations 表
同時交叉比對 115年健保藥價
"""
import sys, io, sqlite3, csv, re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('nhi_drug_coverage.db')
c = conn.cursor()

# Create formulations table
c.execute('DROP TABLE IF EXISTS drug_formulations')
c.execute('''CREATE TABLE drug_formulations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drug_key TEXT NOT NULL,
    brand_name TEXT,
    formulation TEXT,
    dose_mg REAL,
    dose_unit TEXT,
    category TEXT,
    nhi_price REAL,
    ntuh_price REAL,
    nhi_covered INTEGER DEFAULT 1,
    regimen_use TEXT,
    source TEXT DEFAULT 'NTUH 2024/12/05'
)''')

# All formulations from CSV + NHI cross-reference
# Format: (drug_key, brand, formulation, dose_mg, unit, category, nhi_price, ntuh_price, nhi_covered, regimen_use)
FORMULATIONS = [
    # ── Chemotherapy ──
    ('epirubicin', 'Epirubicin', '50mg/25mL/vial', 50, 'vial', 'Chemotherapy', 2366, 2492, 1, 'EC,FEC'),
    ('epirubicin', 'Epirubicin', '10mg/5mL/vial', 10, 'vial', 'Chemotherapy', 398, 382, 1, 'EC,FEC'),
    ('cyclophosphamide', 'Cyclophosphamide', '500mg/vial', 500, 'vial', 'Chemotherapy', 188, 188, 1, 'EC,AC,TC,CMF'),
    ('cyclophosphamide', 'Cyclophosphamide', '200mg/vial', 200, 'vial', 'Chemotherapy', 89, 89, 1, 'EC,AC,TC,CMF'),
    ('cyclophosphamide', 'Cyclophosphamide', '50mg/tab', 50, 'tab', 'Chemotherapy', 15, 15, 1, 'oral_CMF'),
    ('docetaxel', 'Taxotere', '80mg/4mL/vial', 80, 'vial', 'Chemotherapy', 7598, 9874, 1, 'T,TC,THP,TCHP'),
    ('docetaxel', 'Taxotere', '20mg/vial', 20, 'vial', 'Chemotherapy', 2463, 2802, 1, 'T,TC,THP,TCHP'),
    ('carboplatin', 'Carboplatin', '450mg/45mL/vial', 450, 'vial', 'Chemotherapy', 2800, 3195, 1, 'TCHP,TC_carbo'),
    ('carboplatin', 'Carboplatin', '150mg/15mL/vial', 150, 'vial', 'Chemotherapy', 1200, 1442, 1, 'TCHP,TC_carbo'),
    ('paclitaxel', 'Phyxol', '30mg/5mL/vial', 30, 'vial', 'Chemotherapy', 509, 509, 1, 'wP,P'),
    ('paclitaxel', 'Phyxol', '90mg/15mL/vial', 90, 'vial', 'Chemotherapy', 894, 894, 1, 'wP,P'),
    ('doxorubicin_lipo', 'Lipo-Dox', '20mg/10mL/vial', 20, 'vial', 'Chemotherapy', 5274, 12684, 1, 'liposomal'),
    ('vinorelbine', 'Navelbine', '50mg/5mL/vial', 50, 'vial', 'Chemotherapy', 5785, 7238, 1, 'NV'),
    ('vinorelbine', 'Navelbine', '10mg/1mL/vial', 10, 'vial', 'Chemotherapy', 965, 1290, 1, 'NV'),
    ('vinorelbine_oral', 'Navelbine', '30mg/cap', 30, 'cap', 'Chemotherapy', 3945, 3945, 1, 'oral_NV'),
    ('vinorelbine_oral', 'Navelbine', '20mg/cap', 20, 'cap', 'Chemotherapy', 2727, 2727, 1, 'oral_NV'),
    ('capecitabine', 'Xeloda', '500mg/tab', 500, 'tab', 'Chemotherapy', 66, 88, 1, 'X,XP'),
    ('nab_paclitaxel', 'Abraxane', '100mg/vial', 100, 'vial', 'Chemotherapy', 9285, 9285, 1, 'nab-P'),
    ('tegafur_gimeracil', 'TS-1', '20mg/cap', 20, 'cap', 'Chemotherapy', 168, 168, 1, 'TS-1'),
    ('sacituzumab_govitecan', 'Trodelvy', '180mg/vial', 180, 'vial', 'Chemotherapy', 29039, 31943, 1, 'Trodelvy'),
    ('everolimus', 'Afinitor', '5mg/tab', 5, 'tab', 'Chemotherapy', 529, 644, 1, 'Afinitor'),

    # ── Target Therapy ──
    ('trastuzumab_deruxtecan', 'Enhertu', '100mg/vial', 100, 'vial', 'Target Therapy', None, 29771, 0, 'Enhertu'),
    ('trastuzumab_emtansine', 'Kadcyla', '160mg/vial', 160, 'vial', 'Target Therapy', 50983, 56604, 1, 'T-DM1'),
    ('trastuzumab_emtansine', 'Kadcyla', '100mg/vial', 100, 'vial', 'Target Therapy', 31865, 35506, 1, 'T-DM1'),
    ('trastuzumab_sc', 'Herceptin SC', '600mg/5mL/vial', 600, 'vial', 'Target Therapy', 26906, 26906, 1, 'H_SC'),
    ('trastuzumab', 'Herceptin', '440mg/vial', 440, 'vial', 'Target Therapy', 28518, 32885, 1, 'THP,TCHP,H'),
    ('pertuzumab', 'Perjeta', '420mg/14mL/vial', 420, 'vial', 'Target Therapy', 44929, 49966, 1, 'THP,TCHP,HP'),
    ('trastuzumab_biosimilar', 'Herzuma', '440mg/vial', 440, 'vial', 'Target Therapy', 28518, 29895, 1, 'THP,TCHP,H'),
    ('phesgo', 'Phesgo', 'loading dose', 0, 'vial', 'Target Therapy', None, 125306, 0, 'Phesgo'),
    ('phesgo', 'Phesgo', 'maintenance', 0, 'vial', 'Target Therapy', None, 76241, 0, 'Phesgo'),
    ('bevacizumab', 'Avastin', '100mg/4mL/vial', 100, 'vial', 'Target Therapy', 5473, 6810, 1, 'Avastin'),
    ('lapatinib', 'Tykerb', '250mg/tab', 250, 'tab', 'Target Therapy', 351, 351, 1, 'Tykerb'),
    ('neratinib', 'Nerlynx', '40mg/tab', 40, 'tab', 'Target Therapy', 625, 625, 1, 'Nerlynx'),

    # ── Immunotherapy ──
    ('pembrolizumab', 'Keytruda', '100mg/4mL/vial', 100, 'vial', 'Immunotherapy', 54267, 54267, 1, 'Keytruda'),
    ('atezolizumab', 'Tecentriq', '1200mg/20mL/vial', 1200, 'vial', 'Immunotherapy', 91584, 91584, 1, 'Tecentriq'),

    # ── CDK 4/6 Inhibitors ──
    ('palbociclib', 'Ibrance', '125mg/cap', 125, 'cap', 'CDK4/6 Inhibitor', 3665, 3665, 1, 'CDK+AI'),
    ('ribociclib', 'Kisqali', '200mg/tab', 200, 'tab', 'CDK4/6 Inhibitor', 1254, 1254, 1, 'CDK+AI'),
    ('abemaciclib', 'Verzenio', '150mg/tab', 150, 'tab', 'CDK4/6 Inhibitor', 1236, 1236, 1, 'CDK+AI'),

    # ── BRCA Mutation ──
    ('olaparib', 'Lynparza', '150mg/tab', 150, 'tab', 'BRCA Mutation', 1206, 1206, 1, 'Lynparza'),

    # ── PIK3CA Mutation ──
    ('alpelisib', 'Piqray', '250mg daily (200+50mg)', 250, 'box', 'PIK3CA Mutation', 34104, 34104, 1, 'Piqray'),
    ('tucatinib', 'Tukysa', '150mg/tab', 150, 'tab', 'HER2 Target', 240, 28800, 1, 'Tukysa'),

    # ── Antihormone Therapy ──
    ('fulvestrant', 'Faslodex', '250mg/5mL/syringe', 250, 'syringe', 'Antihormone', 17500, 17500, 1, 'Faslodex'),
    ('exemestane', 'Aromasin', '25mg/tab', 25, 'tab', 'Antihormone', 40, 54, 1, 'AI'),
    ('letrozole', 'Femara/Lovizol', '2.5mg/tab', 2.5, 'tab', 'Antihormone', 21, 44, 1, 'AI'),

    # ── Ovarian Suppression ──
    ('goserelin', 'Zoladex', '3.6mg/syringe', 3.6, 'syringe', 'Ovarian Suppression', 3885, 3885, 1, 'GnRHa'),
    ('goserelin', 'Zoladex LA', '10.8mg/syringe', 10.8, 'syringe', 'Ovarian Suppression', 10800, 10800, 1, 'GnRHa'),
    ('leuprolide', 'Leuplin', '3.75mg/syringe', 3.75, 'syringe', 'Ovarian Suppression', 4404, 4404, 1, 'GnRHa'),
    ('triptorelin', 'Diphereline', '11.25mg/vial', 11.25, 'vial', 'Ovarian Suppression', 11489, 11489, 1, 'GnRHa'),

    # ── Bone Agent ──
    ('zoledronic_acid', 'Zobonic', '4mg/vial', 4, 'vial', 'Bone Agent', 3877, 3877, 1, 'bone'),
    ('denosumab', 'Xgeva', '120mg/1.7mL/vial', 120, 'vial', 'RANKL Inhibitor', 10638, 10638, 1, 'bone'),
    ('denosumab_60', 'Prolia', '60mg/1mL/syringe', 60, 'syringe', 'RANKL Inhibitor', 5402, 5402, 1, 'bone'),

    # ── GCSF ──
    ('pegfilgrastim', 'Ziextenzo', '6mg/0.6mL/syringe', 6, 'syringe', 'GCSF', 9685, 9685, 1, 'GCSF'),
    ('pegfilgrastim', 'Fulphila', '6mg/0.6mL/syringe', 6, 'syringe', 'GCSF', 9685, 9685, 1, 'GCSF'),
    ('filgrastim', 'Filgrastim', '300mcg/0.7mL/amp', 0.3, 'amp', 'GCSF', 1967, 1967, 1, 'GCSF'),
    ('lenograstim', 'Granocyte', '100mcg/vial', 0.1, 'vial', 'GCSF', 733, 733, 1, 'GCSF'),

    # ── Antiemetic ──
    ('ondansetron', 'Zofran/Supren', '8mg/4mL/amp', 8, 'amp', 'Antiemetic', 99, 99, 1, 'antiemetic'),
    ('ondansetron_oral', 'Zofran', '8mg/tab', 8, 'tab', 'Antiemetic', 139, 139, 1, 'antiemetic'),
    ('palonosetron', 'Aloxi', '0.25mg/5mL/vial', 0.25, 'vial', 'Antiemetic', 822, 822, 1, 'antiemetic'),
    ('granisetron', 'Kytril', '3mg/3mL/amp', 3, 'amp', 'Antiemetic', 359, 359, 1, 'antiemetic'),
    ('granisetron_oral', 'Kytril', '1mg/tab', 1, 'tab', 'Antiemetic', 194, 194, 1, 'antiemetic'),
    ('fosaprepitant', 'Emend IV', '150mg/vial', 150, 'vial', 'Antiemetic', 1803, 1803, 1, 'antiemetic'),
    ('aprepitant_125', 'Emend', '125mg/cap', 125, 'cap', 'Antiemetic', 498, 498, 1, 'antiemetic'),
    ('aprepitant_80', 'Emend', '80mg/cap', 80, 'cap', 'Antiemetic', 498, 498, 1, 'antiemetic'),
    ('olanzapine', 'Zyprexa Zydis', '5mg/tab', 5, 'tab', 'Antiemetic', 43, 43, 1, 'antiemetic'),

    # ── Other ──
    ('oncotype_dx', 'Oncotype DX', 'Genomic Test', 0, 'test', 'Genetic Test', None, 170000, 0, 'diagnostic'),
    ('ice_cooling', 'ICE Hat & Glove', 'Cooling System', 0, 'set', 'Supportive', None, 18850, 0, 'supportive'),
]

inserted = 0
for rec in FORMULATIONS:
    c.execute('''INSERT INTO drug_formulations
        (drug_key, brand_name, formulation, dose_mg, dose_unit, category, nhi_price, ntuh_price, nhi_covered, regimen_use)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', rec)
    inserted += 1

conn.commit()

# Stats
c.execute('SELECT COUNT(*) FROM drug_formulations')
total = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM drug_formulations WHERE nhi_price IS NOT NULL')
with_nhi = c.fetchone()[0]
c.execute('SELECT COUNT(DISTINCT drug_key) FROM drug_formulations')
unique_drugs = c.fetchone()[0]
c.execute('SELECT COUNT(DISTINCT category) FROM drug_formulations')
categories = c.fetchone()[0]

conn.close()

print(f'匯入完成：{total} 筆品項')
print(f'涵蓋 {unique_drugs} 種藥物，{categories} 個類別')
print(f'有健保價格：{with_nhi}/{total}')
print(f'來源：台大醫院藥品價目表 (2024/12/05)')
