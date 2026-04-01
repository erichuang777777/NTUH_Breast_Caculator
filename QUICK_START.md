# Quick Start Guide - NHI Drug Coverage System

## 5-Minute Setup

### Step 1: Verify Installation
```bash
cd D:\drug_appli
python3 -c "import sqlite3; print('Python ready')"
```

### Step 2: Check Database
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM drugs")
count = cursor.fetchone()[0]
print(f"Total drugs in database: {count}")
conn.close()
EOF
```

Expected output: `Total drugs in database: 89`

## Using the Query Tool (For Doctors)

### Interactive Menu
```bash
python query_tool.py
```

### Options:
```
1. Search Breast Cancer drugs       → Find breast cancer medications
2. Search Hematologic drugs         → Find blood cancer medications
3. List all drugs                   → View complete drug database
4. Get drug details                 → View coverage requirements
5. Exit                             → Quit the program
```

### Example Usage:
```
Select option (1-5): 1
Enter drug name (or press Enter for all): trastuzumab
Found 1 drug(s):
  [1] Trastuzumab
Select drug number (or press Enter to skip): 1
[Drug] Trastuzumab
...coverage details...
```

## Database Query (For Developers)

### View All Breast Cancer Drugs
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT generic_name FROM drugs
    WHERE specialty_id = 'oncology_breast'
    ORDER BY generic_name
""")
for drug in cursor.fetchall():
    print(f"  - {drug[0]}")
conn.close()
EOF
```

### Search for Specific Drug
```bash
python3 << 'EOF'
import sqlite3
drug_name = 'Trastuzumab'  # Change this
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT id, generic_name, specialty_id FROM drugs
    WHERE generic_name LIKE ?
    ORDER BY generic_name
""", (f'%{drug_name}%',))
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Name: {row[1]}, Type: {row[2]}")
conn.close()
EOF
```

## Updating the Database

### Automatic Update (Check NHI website)
```bash
python auto_updater.py
```

### Re-parse Current Document
```bash
python filtered_parser.py
```

## Database Statistics

### Quick Stats
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()

# Count by specialty
cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_breast'")
print(f"Breast Cancer drugs: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM drugs WHERE specialty_id = 'oncology_heme'")
print(f"Hematologic drugs: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM drugs")
print(f"Total: {cursor.fetchone()[0]}")

conn.close()
EOF
```

## Common Tasks

### Export Drug List to Text
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()

with open('breast_cancer_drugs.txt', 'w', encoding='utf-8') as f:
    cursor.execute("SELECT generic_name FROM drugs WHERE specialty_id = 'oncology_breast' ORDER BY generic_name")
    for drug in cursor.fetchall():
        f.write(drug[0] + '\n')

print("Exported to breast_cancer_drugs.txt")
conn.close()
EOF
```

### Find Drugs with Specific Pattern
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()

# Find drugs containing 'trastuzumab'
pattern = '%trastuzumab%'
cursor.execute("""
    SELECT generic_name FROM drugs
    WHERE LOWER(generic_name) LIKE LOWER(?)
    ORDER BY generic_name
""", (pattern,))

results = cursor.fetchall()
print(f"Found {len(results)} drug(s):")
for drug in results:
    print(f"  - {drug[0]}")

conn.close()
EOF
```

## Troubleshooting

### "No module named sqlite3"
**Solution**: sqlite3 is built-in. Try:
```bash
python3 -m sqlite3
```

### Database locked error
**Solution**: Close all other programs accessing the database, then try again.

### "File not found" error
**Make sure you're in the right directory:**
```bash
cd D:\drug_appli
ls -la nhi_drug_coverage.db    # Should show the file
```

### Query returns no results
**Check specialty_id values:**
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('nhi_drug_coverage.db')
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT specialty_id FROM drugs")
for row in cursor.fetchall():
    print(row[0])
conn.close()
EOF
```

## File Locations

```
D:\drug_appli\
├── nhi_drug_coverage.db         ← Main database
├── query_tool.py                ← Doctor query tool
├── auto_updater.py              ← Update mechanism
├── filtered_parser.py           ← Drug extraction
├── smart_filter.py              ← Quality filtering
├── known_oncology_drugs.py      ← Reference lists
├── 完整給付規定1150323.docx     ← Source document
├── README.md                    ← Full documentation
└── QUICK_START.md               ← This file
```

## System Status

| Component | Status | Command |
|-----------|--------|---------|
| Database | ✓ Ready | `python3 << 'EOF'` |
| Query Tool | ✓ Ready | `python query_tool.py` |
| Parser | ✓ Ready | `python filtered_parser.py` |
| Auto-Update | ✓ Ready | `python auto_updater.py` |

## Key Statistics

- **Breast Cancer Drugs**: 71
- **Hematologic Drugs**: 18
- **Total**: 89
- **Database Size**: ~500 KB
- **Last Updated**: 2026-03-31

## Next Steps

1. **Doctors**: Run `python query_tool.py` to start querying drugs
2. **Admins**: Run `python auto_updater.py` weekly to check for updates
3. **Developers**: Review `README.md` for API details

---

**Need help?** See `README.md` for comprehensive documentation.
