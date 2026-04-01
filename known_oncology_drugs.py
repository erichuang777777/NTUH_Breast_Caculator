#!/usr/bin/env python3
"""
Known Oncology Drug Lists
Comprehensive list of breast cancer and hematologic malignancy drugs
"""

# Breast Cancer Drugs
BREAST_CANCER_DRUGS = {
    # HER2-targeted
    'Trastuzumab', 'Herceptin', 'Pertuzumab', 'Perjeta', 'Lapatinib', 'Tykerb',
    'Trastuzumab emtansine', 'Kadcyla', 'Trastuzumab deruxtecan', 'Enhertu',
    'Margetuximab', 'Zenocutuzumab',

    # CDK4/6 Inhibitors
    'Palbociclib', 'Ibrance', 'Ribociclib', 'Kisqali', 'Alpelisib', 'Piqray',

    # Aromatase Inhibitors
    'Anastrozole', 'Arimidex', 'Letrozole', 'Femara', 'Exemestane', 'Aromasin',

    # Selective Estrogen Receptor Modulator
    'Tamoxifen', 'Nolvadex',

    # Selective Estrogen Receptor Degrader
    'Fulvestrant', 'Faslodex',

    # Chemotherapy
    'Paclitaxel', 'Taxol', 'Docetaxel', 'Taxotere', 'Doxorubicin', 'Adriamycin',
    'Capecitabine', 'Xeloda', 'Fluorouracil', '5FU', 'Cyclophosphamide', 'Cytoxan',
    'Gemcitabine', 'Gemzar', 'Vinorelbine', 'Navelbine',

    # Targeted Therapy
    'Bevacizumab', 'Avastin', 'Ramucirumab', 'Cyramza', 'Everolimus', 'Afinitor',
    'Olaparib', 'Lynparza', 'Rucaparib', 'Rubraca', 'Niraparib', 'Zejula',
    'Talazoparib', 'Talquetamab', 'Tucatinib', 'Tukysa',

    # HER2-low therapies
    'Sacituzumab govitecan', 'Trodelvy', 'Datopotamab deruxtecan', 'Dato-DXd',

    # PIK3CA Inhibitor
    'Alpelisib', 'Piqray',

    # Hormone therapy
    'Megestrol acetate', 'Megace',
}

# Hematologic Malignancy Drugs
HEME_MALIGNANCY_DRUGS = {
    # Lymphoma drugs
    'Rituximab', 'Rituxan', 'Obinutuzumab', 'Gazyva', 'Ofatumumab', 'Arzerra',
    'Ibritumomab tiuxetan', 'Zevalin', 'Tositumomab', 'Bexxar',
    'Brentuximab vedotin', 'Adcetris', 'Nivolumab', 'Opdivo',
    'Pembrolizumab', 'Keytruda', 'Atezolizumab', 'Tecentriq',

    # Multiple Myeloma drugs
    'Bortezomib', 'Velcade', 'Carfilzomib', 'Kyprolis', 'Ixazomib', 'Ninlaro',
    'Lenalidomide', 'Revlimid', 'Pomalidomide', 'Pomalyst', 'Thalidomide', 'Thalomid',
    'Daratumumab', 'Darzalex', 'Elotuzumab', 'Empliciti',
    'Panobinostat', 'Farydak', 'Vorinostat', 'Zolinza',

    # CLL/SLL drugs
    'Ibrutinib', 'Imbruvica', 'Acalabrutinib', 'Calquence', 'Zanabrutinib', 'Brukinsa',
    'Venetoclax', 'Venclexta', 'Idelalisib', 'Zydelig',
    'Obinutuzumab', 'Gazyva', 'Ofatumumab', 'Arzerra',

    # CML drugs
    'Imatinib', 'Gleevec', 'Dasatinib', 'Sprycel', 'Nilotinib', 'Tasigna',
    'Ponatinib', 'Iclusig', 'Bosutinib', 'Bosulif',

    # AML drugs
    'Azacitidine', 'Vidaza', 'Decitabine', 'Dacogen', 'Venetoclax', 'Venclexta',
    'Ivosidenib', 'Idhifa', 'Enasidenib', 'Idhifa', 'Gilteritinib', 'Xospata',
    'Midostaurin', 'Rydapt', 'Sorafenib', 'Nexavar',
    'Arsenic trioxide', 'Trisenox', 'Daunorubicin', 'Daunomycin',
    'Cytarabine', 'Ara-C', 'Etoposide', 'Vepesid',

    # Chemotherapy (generic)
    'Doxorubicin', 'Adriamycin', 'Bleomycin', 'Blenoxane',
    'Cisplatin', 'Carboplatin', 'Oxaliplatin', 'Eloxatin',
    'Vincristine', 'Oncovin', 'Vinblastine', 'Velban',
    'Methylprednisolone', 'Dexamethasone',
    'Cyclophosphamide', 'Cytoxan', 'Bendamustine', 'Treanda',
    'Fludarabine', 'Fludara', 'Cladribine', 'Leustatin',
    'Pentostatin', 'Nipent',

    # Immunotherapy
    'Nivolumab', 'Opdivo', 'Pembrolizumab', 'Keytruda',
    'Atezolizumab', 'Tecentriq', 'Durvalumab', 'Imfinzi',

    # CAR-T
    'Tisagenlecleucel', 'Kymriah', 'Axicabtagene ciloleucel', 'Yescarta',
    'Brexucabtagene autoleucel', 'Tecartus',
}

def is_known_oncology_drug(drug_name: str) -> bool:
    """Check if a drug name is in the known oncology drug lists"""
    # Normalize the name
    name_lower = drug_name.lower().strip()

    # Check both lists
    for drug in BREAST_CANCER_DRUGS:
        if name_lower == drug.lower():
            return True

    for drug in HEME_MALIGNANCY_DRUGS:
        if name_lower == drug.lower():
            return True

    return False
