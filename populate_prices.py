#!/usr/bin/env python3
"""Populate drug prices into database"""
import sys, io, sqlite3, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('nhi_drug_coverage.db')
c = conn.cursor()

# Add columns if not exist
for col, typ in [('nhi_price', 'REAL DEFAULT NULL'), ('price_unit', 'TEXT DEFAULT ""'), ('dosage_info', 'TEXT DEFAULT ""')]:
    try:
        c.execute(f'ALTER TABLE drugs ADD COLUMN {col} {typ}')
        print(f'Added {col} column')
    except:
        print(f'{col} column exists')

# NHI drug prices (approximate, per unit/vial/tablet)
# Based on published 健保藥價基準
prices = {
    # HER2-targeted (breast)
    'Trastuzumab':    (18741, '440mg/vial', {'type':'iv','dose_per_kg':6,'unit':'mg/kg','freq':'q3w','cycles':18,'note':'首次8mg/kg，之後6mg/kg，每3週一次'}),
    'Herceptin':      (18741, '440mg/vial', {'type':'iv','dose_per_kg':6,'unit':'mg/kg','freq':'q3w','cycles':18,'note':'首次8mg/kg，之後6mg/kg，每3週一次'}),
    'Pertuzumab':     (58752, '420mg/vial', {'type':'iv','dose_fixed':420,'unit':'mg','freq':'q3w','cycles':18,'note':'固定劑量420mg，每3週一次'}),
    'Perjeta':        (58752, '420mg/vial', {'type':'iv','dose_fixed':420,'unit':'mg','freq':'q3w','cycles':18,'note':'固定劑量420mg，每3週一次'}),
    'Trastuzumab emtansine': (72845, '100mg/vial', {'type':'iv','dose_per_kg':3.6,'unit':'mg/kg','freq':'q3w','cycles':14,'note':'3.6mg/kg，每3週一次'}),
    'Kadcyla':        (72845, '100mg/vial', {'type':'iv','dose_per_kg':3.6,'unit':'mg/kg','freq':'q3w','cycles':14,'note':'3.6mg/kg，每3週一次'}),
    'Trastuzumab deruxtecan': (95263, '100mg/vial', {'type':'iv','dose_per_kg':5.4,'unit':'mg/kg','freq':'q3w','cycles':None,'note':'5.4mg/kg，每3週一次，使用至疾病惡化'}),
    'Enhertu':        (95263, '100mg/vial', {'type':'iv','dose_per_kg':5.4,'unit':'mg/kg','freq':'q3w','cycles':None,'note':'5.4mg/kg，每3週一次，使用至疾病惡化'}),
    'Lapatinib':      (73, '250mg/tab', {'type':'oral','dose_fixed':1250,'unit':'mg','freq':'daily','note':'1250mg/日（5錠），每日一次'}),
    'Tykerb':         (73, '250mg/tab', {'type':'oral','dose_fixed':1250,'unit':'mg','freq':'daily','note':'1250mg/日（5錠），每日一次'}),

    # CDK4/6 inhibitors
    'Palbociclib':    (3520, '125mg/cap', {'type':'oral','dose_fixed':125,'unit':'mg','freq':'daily','schedule':'21/28','note':'125mg/日，21天服藥/7天休息'}),
    'Ribociclib':     (2500, '200mg/tab', {'type':'oral','dose_fixed':600,'unit':'mg','freq':'daily','schedule':'21/28','note':'600mg/日（3錠），21天服藥/7天休息'}),

    # Aromatase inhibitors
    'Anastrozole':    (40, '1mg/tab', {'type':'oral','dose_fixed':1,'unit':'mg','freq':'daily','note':'1mg/日'}),
    'Arimidex':       (40, '1mg/tab', {'type':'oral','dose_fixed':1,'unit':'mg','freq':'daily','note':'1mg/日'}),
    'Letrozole':      (42, '2.5mg/tab', {'type':'oral','dose_fixed':2.5,'unit':'mg','freq':'daily','note':'2.5mg/日'}),
    'Exemestane':     (85, '25mg/tab', {'type':'oral','dose_fixed':25,'unit':'mg','freq':'daily','note':'25mg/日'}),
    'Tamoxifen':      (3, '10mg/tab', {'type':'oral','dose_fixed':20,'unit':'mg','freq':'daily','note':'20mg/日（2錠）'}),
    'Fulvestrant':    (16849, '250mg/syringe', {'type':'im','dose_fixed':500,'unit':'mg','freq':'q4w','note':'500mg/月（2支），首月第1、15天各一次'}),

    # Chemo
    'Paclitaxel':     (3850, '100mg/vial', {'type':'iv','dose_per_bsa':175,'unit':'mg/m2','freq':'q3w','note':'175mg/m2，每3週一次'}),
    'Docetaxel':      (4200, '80mg/vial', {'type':'iv','dose_per_bsa':75,'unit':'mg/m2','freq':'q3w','note':'75mg/m2，每3週一次'}),
    'Capecitabine':   (35, '500mg/tab', {'type':'oral','dose_per_bsa':1000,'unit':'mg/m2','freq':'bid','schedule':'14/21','note':'1000mg/m2 BID，14天服藥/7天休息'}),
    'Doxorubicin':    (570, '50mg/vial', {'type':'iv','dose_per_bsa':60,'unit':'mg/m2','freq':'q3w','note':'60mg/m2，每3週一次'}),
    'Gemcitabine':    (2800, '1g/vial', {'type':'iv','dose_per_bsa':1000,'unit':'mg/m2','freq':'weekly','schedule':'3/4','note':'1000mg/m2，每週一次x3週，休1週'}),
    'Fluorouracil':   (22, '250mg/vial', {'type':'iv','dose_per_bsa':600,'unit':'mg/m2','freq':'q3w','note':'600mg/m2'}),
    'Cyclophosphamide': (120, '200mg/tab', {'type':'oral_or_iv','dose_per_bsa':600,'unit':'mg/m2','freq':'q3w','note':'600mg/m2 IV q3w 或 oral'}),
    'Vinorelbine':    (3250, '50mg/vial', {'type':'iv','dose_per_bsa':25,'unit':'mg/m2','freq':'weekly','note':'25mg/m2，每週一次'}),

    # Targeted (breast)
    'Bevacizumab':    (13462, '100mg/vial', {'type':'iv','dose_per_kg':10,'unit':'mg/kg','freq':'q2w','note':'10mg/kg，每2週一次'}),
    'Avastin':        (13462, '100mg/vial', {'type':'iv','dose_per_kg':10,'unit':'mg/kg','freq':'q2w','note':'10mg/kg，每2週一次'}),
    'Everolimus':     (2890, '10mg/tab', {'type':'oral','dose_fixed':10,'unit':'mg','freq':'daily','note':'10mg/日'}),
    'Olaparib':       (1105, '150mg/tab', {'type':'oral','dose_fixed':300,'unit':'mg','freq':'bid','note':'300mg BID（每次2錠）'}),
    'Alpelisib':      (1800, '150mg/tab', {'type':'oral','dose_fixed':300,'unit':'mg','freq':'daily','note':'300mg/日（2錠）'}),
    'Piqray':         (1800, '150mg/tab', {'type':'oral','dose_fixed':300,'unit':'mg','freq':'daily','note':'300mg/日（2錠）'}),
    'Sacituzumab govitecan': (48500, '180mg/vial', {'type':'iv','dose_per_kg':10,'unit':'mg/kg','freq':'weekly','schedule':'2/3','note':'10mg/kg，第1、8天，每3週一次'}),
    'Niraparib':      (1580, '100mg/cap', {'type':'oral','dose_fixed':200,'unit':'mg','freq':'daily','note':'200mg/日（2粒）'}),
    'Talazoparib':    (3200, '1mg/cap', {'type':'oral','dose_fixed':1,'unit':'mg','freq':'daily','note':'1mg/日'}),

    # CML drugs
    'Imatinib':       (72, '100mg/tab', {'type':'oral','dose_fixed':400,'unit':'mg','freq':'daily','note':'400mg/日（4錠）'}),
    'Dasatinib':      (1780, '50mg/tab', {'type':'oral','dose_fixed':100,'unit':'mg','freq':'daily','note':'100mg/日（2錠）'}),
    'Sprycel':        (1780, '50mg/tab', {'type':'oral','dose_fixed':100,'unit':'mg','freq':'daily','note':'100mg/日（2錠）'}),
    'Nilotinib':      (1450, '200mg/cap', {'type':'oral','dose_fixed':400,'unit':'mg','freq':'bid','note':'400mg BID（每次2粒）'}),
    'Tasigna':        (1450, '200mg/cap', {'type':'oral','dose_fixed':400,'unit':'mg','freq':'bid','note':'400mg BID（每次2粒）'}),
    'Ponatinib':      (3850, '15mg/tab', {'type':'oral','dose_fixed':45,'unit':'mg','freq':'daily','note':'45mg/日（3錠）'}),
    'Iclusig':        (3850, '15mg/tab', {'type':'oral','dose_fixed':45,'unit':'mg','freq':'daily','note':'45mg/日（3錠）'}),
    'Bosutinib':      (2100, '100mg/tab', {'type':'oral','dose_fixed':500,'unit':'mg','freq':'daily','note':'500mg/日（5錠）'}),

    # MM drugs
    'Bortezomib':     (17500, '3.5mg/vial', {'type':'sc_iv','dose_per_bsa':1.3,'unit':'mg/m2','freq':'biweekly','note':'1.3mg/m2，每週2次x2週，休10天'}),
    'Velcade':        (17500, '3.5mg/vial', {'type':'sc_iv','dose_per_bsa':1.3,'unit':'mg/m2','freq':'biweekly','note':'1.3mg/m2，每週2次x2週，休10天'}),
    'Lenalidomide':   (8960, '25mg/cap', {'type':'oral','dose_fixed':25,'unit':'mg','freq':'daily','schedule':'21/28','note':'25mg/日，21天服藥/7天休息'}),
    'Revlimid':       (8960, '25mg/cap', {'type':'oral','dose_fixed':25,'unit':'mg','freq':'daily','schedule':'21/28','note':'25mg/日，21天服藥/7天休息'}),
    'Pomalidomide':   (9200, '4mg/cap', {'type':'oral','dose_fixed':4,'unit':'mg','freq':'daily','schedule':'21/28','note':'4mg/日，21天服藥/7天休息'}),
    'Pomalyst':       (9200, '4mg/cap', {'type':'oral','dose_fixed':4,'unit':'mg','freq':'daily','schedule':'21/28','note':'4mg/日，21天服藥/7天休息'}),
    'Carfilzomib':    (25800, '60mg/vial', {'type':'iv','dose_per_bsa':56,'unit':'mg/m2','freq':'biweekly','note':'56mg/m2，每週2次x3週，休1週'}),
    'Thalidomide':    (350, '100mg/cap', {'type':'oral','dose_fixed':200,'unit':'mg','freq':'daily','note':'200mg/日（2粒）'}),

    # CLL/lymphoma drugs
    'Ibrutinib':      (3780, '140mg/cap', {'type':'oral','dose_fixed':420,'unit':'mg','freq':'daily','note':'CLL: 420mg/日（3粒）'}),
    'Imbruvica':      (3780, '140mg/cap', {'type':'oral','dose_fixed':420,'unit':'mg','freq':'daily','note':'CLL: 420mg/日（3粒）'}),
    'Acalabrutinib':  (2950, '100mg/cap', {'type':'oral','dose_fixed':200,'unit':'mg','freq':'bid','note':'100mg BID（每日2粒）'}),
    'Venetoclax':     (2850, '100mg/tab', {'type':'oral','dose_fixed':400,'unit':'mg','freq':'daily','note':'400mg/日（漸進增量後），4錠'}),
    'Venclexta':      (2850, '100mg/tab', {'type':'oral','dose_fixed':400,'unit':'mg','freq':'daily','note':'400mg/日（漸進增量後），4錠'}),
    'Zanubrutinib':   (2780, '80mg/cap', {'type':'oral','dose_fixed':320,'unit':'mg','freq':'daily_or_bid','note':'320mg/日 或 160mg BID'}),
    'Rituximab':      (19430, '500mg/vial', {'type':'iv','dose_per_bsa':375,'unit':'mg/m2','freq':'weekly','cycles':4,'note':'375mg/m2，每週一次x4-8次'}),
    'Obinutuzumab':   (32000, '1000mg/vial', {'type':'iv','dose_fixed':1000,'unit':'mg','freq':'q4w','note':'1000mg，第一週期每週，之後每4週'}),
    'Brentuximab vedotin': (78000, '50mg/vial', {'type':'iv','dose_per_kg':1.8,'unit':'mg/kg','freq':'q3w','cycles':16,'note':'1.8mg/kg，每3週一次'}),
    'Bendamustine':   (14500, '100mg/vial', {'type':'iv','dose_per_bsa':90,'unit':'mg/m2','freq':'q4w','schedule':'2/28','note':'90mg/m2/日x2天，每28天一週期'}),
    'Fludarabine':    (5800, '50mg/vial', {'type':'iv','dose_per_bsa':25,'unit':'mg/m2','freq':'daily','schedule':'5/28','note':'25mg/m2/日x5天，每28天一週期'}),
    'Fludara':        (5800, '50mg/vial', {'type':'iv','dose_per_bsa':25,'unit':'mg/m2','freq':'daily','schedule':'5/28','note':'25mg/m2/日x5天，每28天一週期'}),

    # AML drugs
    'Azacitidine':    (8900, '100mg/vial', {'type':'sc','dose_per_bsa':75,'unit':'mg/m2','freq':'daily','schedule':'7/28','note':'75mg/m2/日x7天，每28天一週期'}),
    'Vidaza':         (8900, '100mg/vial', {'type':'sc','dose_per_bsa':75,'unit':'mg/m2','freq':'daily','schedule':'7/28','note':'75mg/m2/日x7天，每28天一週期'}),
    'Decitabine':     (15600, '50mg/vial', {'type':'iv','dose_per_bsa':20,'unit':'mg/m2','freq':'daily','schedule':'5/28','note':'20mg/m2/日x5天，每28天一週期'}),
    'Gilteritinib':   (6250, '40mg/tab', {'type':'oral','dose_fixed':120,'unit':'mg','freq':'daily','note':'120mg/日（3錠）'}),
    'Midostaurin':    (12500, '25mg/cap', {'type':'oral','dose_fixed':50,'unit':'mg','freq':'bid','note':'50mg BID，搭配化療'}),
    'Cytarabine':     (280, '100mg/vial', {'type':'iv','dose_per_bsa':200,'unit':'mg/m2','freq':'daily','schedule':'7/28','note':'200mg/m2/日x7天'}),
    'Ara-C':          (280, '100mg/vial', {'type':'iv','dose_per_bsa':200,'unit':'mg/m2','freq':'daily','schedule':'7/28','note':'200mg/m2/日x7天'}),
    'Oxaliplatin':    (4500, '100mg/vial', {'type':'iv','dose_per_bsa':85,'unit':'mg/m2','freq':'q2w','note':'85mg/m2，每2週一次'}),

    # Other
    'Osimertinib':    (5680, '80mg/tab', {'type':'oral','dose_fixed':80,'unit':'mg','freq':'daily','note':'80mg/日'}),
    'Erlotinib':      (1950, '150mg/tab', {'type':'oral','dose_fixed':150,'unit':'mg','freq':'daily','note':'150mg/日'}),
    'Sorafenib':      (2200, '200mg/tab', {'type':'oral','dose_fixed':800,'unit':'mg','freq':'daily','note':'800mg/日（4錠）'}),
    'Lenvatinib':     (2400, '10mg/cap', {'type':'oral','dose_fixed':24,'unit':'mg','freq':'daily','note':'24mg/日'}),
    'Elotuzumab':     (28500, '400mg/vial', {'type':'iv','dose_per_kg':10,'unit':'mg/kg','freq':'q2w_to_q4w','note':'10mg/kg，前2週期每週，之後每2週'}),
    'Dexamethasone':  (5, '4mg/tab', {'type':'oral','dose_fixed':40,'unit':'mg','freq':'weekly','note':'40mg/週（10錠）'}),
    'Cetuximab':      (12600, '100mg/vial', {'type':'iv','dose_per_bsa':400,'unit':'mg/m2','freq':'weekly','note':'首次400mg/m2，之後250mg/m2每週'}),
    'Ramucirumab':    (26800, '500mg/vial', {'type':'iv','dose_per_kg':8,'unit':'mg/kg','freq':'q2w','note':'8mg/kg，每2週一次'}),
}

updated = 0
for drug_name, (price, unit, dosage) in prices.items():
    dosage_json = json.dumps(dosage, ensure_ascii=False)
    c.execute('UPDATE drugs SET nhi_price=?, price_unit=?, dosage_info=? WHERE generic_name=?',
              (price, unit, dosage_json, drug_name))
    if c.rowcount > 0:
        updated += 1

conn.commit()

# Stats
c.execute('SELECT COUNT(*) FROM drugs WHERE nhi_price IS NOT NULL')
with_price = c.fetchone()[0]
c.execute('SELECT COUNT(*) FROM drugs')
total = c.fetchone()[0]
print(f'\nDrugs with price data: {with_price}/{total}')
print(f'Updated: {updated} drugs')

# Show top-10 most expensive
c.execute('SELECT generic_name, nhi_price, price_unit FROM drugs WHERE nhi_price IS NOT NULL ORDER BY nhi_price DESC LIMIT 10')
print('\nTop 10 most expensive (per unit):')
for r in c.fetchall():
    print(f'  {r[0]:<30} NT${r[1]:>8,.0f} / {r[2]}')

conn.close()
