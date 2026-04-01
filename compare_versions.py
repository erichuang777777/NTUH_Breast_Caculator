#!/usr/bin/env python3
"""
NHI Drug Coverage Version Comparator (Standalone)
比較兩個版本的 DOCX 文檔，視覺化顯示差異

Usage:
    python compare_versions.py <old_docx> <new_docx>
    python compare_versions.py <old_docx> <new_docx> -o diff_report.html
    python compare_versions.py <old_docx> <new_docx> --json
"""

import sys
import io
import zipfile
import xml.etree.ElementTree as ET
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict, Set, Tuple
from difflib import SequenceMatcher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def load_docx_paragraphs(docx_path: str) -> List[str]:
    """載入 DOCX 段落"""
    with zipfile.ZipFile(docx_path, 'r') as z:
        xml_data = z.read('word/document.xml')
    root = ET.fromstring(xml_data)
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

    paragraphs = []
    for para in root.findall('.//w:p', ns):
        text_elements = para.findall('.//w:t', ns)
        text = ''.join([t.text for t in text_elements if t.text])
        if text.strip():
            paragraphs.append(text.strip())
    return paragraphs


def extract_drug_sections(paragraphs: List[str]) -> Dict[str, dict]:
    """提取所有藥物章節"""
    sections = {}
    section_pattern = re.compile(r'^(\d+\.[\d.]*)\s*([A-Z][A-Za-z\s\-/]+)')

    i = 0
    while i < len(paragraphs):
        m = section_pattern.match(paragraphs[i])
        if m:
            section_id = m.group(1)
            drug_name = m.group(2).strip()

            # Find section end
            parts = [p for p in section_id.split('.') if p]
            if len(parts) >= 2:
                parent = parts[0]
                next_pat = re.compile(
                    r'^' + re.escape(parent) + r'\.\d+\.?\s*[A-Z\u4e00-\u9fff]'
                )
            else:
                next_pat = re.compile(r'^\d+\.\s*[A-Z\u4e00-\u9fff]')

            end = i + 1
            for j in range(i + 1, min(i + 300, len(paragraphs))):
                if next_pat.match(paragraphs[j]):
                    nm = re.match(r'^(\d+\.[\d.]*)', paragraphs[j])
                    if nm and nm.group(1) != section_id:
                        end = j
                        break
                end = j + 1

            section_text = paragraphs[i:end]
            sections[drug_name] = {
                'section_id': section_id,
                'header': paragraphs[i],
                'text': section_text,
                'full_text': '\n'.join(section_text),
                'line_count': len(section_text),
            }
            i = end
        else:
            i += 1

    return sections


def compare_versions(old_path: str, new_path: str) -> dict:
    """比較兩個版本"""
    old_paras = load_docx_paragraphs(old_path)
    new_paras = load_docx_paragraphs(new_path)

    old_sections = extract_drug_sections(old_paras)
    new_sections = extract_drug_sections(new_paras)

    old_drugs = set(old_sections.keys())
    new_drugs = set(new_sections.keys())

    added = sorted(new_drugs - old_drugs)
    removed = sorted(old_drugs - new_drugs)
    common = sorted(old_drugs & new_drugs)

    # Compare common drugs for changes
    modified = []
    unchanged = []
    for drug in common:
        old_text = old_sections[drug]['full_text']
        new_text = new_sections[drug]['full_text']

        if old_text == new_text:
            unchanged.append(drug)
        else:
            ratio = SequenceMatcher(None, old_text, new_text).ratio()
            # Generate line-level diff
            old_lines = old_text.split('\n')
            new_lines = new_text.split('\n')
            diff_lines = []
            sm = SequenceMatcher(None, old_lines, new_lines)
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op == 'equal':
                    for line in old_lines[i1:i2]:
                        diff_lines.append(('equal', line))
                elif op == 'delete':
                    for line in old_lines[i1:i2]:
                        diff_lines.append(('removed', line))
                elif op == 'insert':
                    for line in new_lines[j1:j2]:
                        diff_lines.append(('added', line))
                elif op == 'replace':
                    for line in old_lines[i1:i2]:
                        diff_lines.append(('removed', line))
                    for line in new_lines[j1:j2]:
                        diff_lines.append(('added', line))

            added_count = sum(1 for t, _ in diff_lines if t == 'added')
            removed_count = sum(1 for t, _ in diff_lines if t == 'removed')

            modified.append({
                'drug': drug,
                'similarity': round(ratio, 3),
                'old_lines': len(old_lines),
                'new_lines': len(new_lines),
                'added_lines': added_count,
                'removed_lines': removed_count,
                'diff': diff_lines,
            })

    return {
        'old_file': old_path,
        'new_file': new_path,
        'old_paragraphs': len(old_paras),
        'new_paragraphs': len(new_paras),
        'old_drug_sections': len(old_sections),
        'new_drug_sections': len(new_sections),
        'added': added,
        'removed': removed,
        'modified': modified,
        'unchanged': unchanged,
        'summary': {
            'added_count': len(added),
            'removed_count': len(removed),
            'modified_count': len(modified),
            'unchanged_count': len(unchanged),
        },
    }


def generate_html_report(result: dict) -> str:
    """生成 HTML 差異報告"""
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>NHI 給付規定版本差異報告</title>
<style>
body {{ font-family: 'Microsoft JhengHei', 'Segoe UI', sans-serif; margin: 20px; background: #f5f5f5; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ color: #1a5276; border-bottom: 3px solid #2980b9; padding-bottom: 10px; }}
h2 {{ color: #2c3e50; margin-top: 30px; }}
.summary {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0; }}
.stat {{ display: inline-block; margin: 10px 20px; text-align: center; }}
.stat-num {{ font-size: 36px; font-weight: bold; }}
.stat-label {{ color: #7f8c8d; font-size: 14px; }}
.added {{ color: #27ae60; }}
.removed {{ color: #e74c3c; }}
.modified {{ color: #f39c12; }}
.unchanged {{ color: #95a5a6; }}
.drug-list {{ background: white; padding: 15px; border-radius: 8px; margin: 10px 0; }}
.drug-item {{ padding: 5px 10px; margin: 3px 0; border-radius: 4px; }}
.drug-added {{ background: #d5f5e3; border-left: 4px solid #27ae60; }}
.drug-removed {{ background: #fadbd8; border-left: 4px solid #e74c3c; }}
.diff-block {{ background: white; padding: 15px; border-radius: 8px; margin: 15px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.diff-header {{ font-weight: bold; font-size: 16px; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee; }}
.diff-line {{ font-family: 'Consolas', monospace; font-size: 13px; padding: 2px 8px; white-space: pre-wrap; }}
.line-added {{ background: #d5f5e3; color: #1e8449; }}
.line-removed {{ background: #fadbd8; color: #c0392b; text-decoration: line-through; }}
.line-equal {{ color: #7f8c8d; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; color: white; }}
.badge-added {{ background: #27ae60; }}
.badge-removed {{ background: #e74c3c; }}
</style>
</head>
<body>
<div class="container">
<h1>NHI 給付規定版本差異報告</h1>
<div class="summary">
    <p><strong>舊版:</strong> {result['old_file']} ({result['old_paragraphs']} 段落, {result['old_drug_sections']} 藥物章節)</p>
    <p><strong>新版:</strong> {result['new_file']} ({result['new_paragraphs']} 段落, {result['new_drug_sections']} 藥物章節)</p>
    <p><strong>比較時間:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr>
    <div style="text-align:center">
        <div class="stat"><div class="stat-num added">+{result['summary']['added_count']}</div><div class="stat-label">新增藥物</div></div>
        <div class="stat"><div class="stat-num removed">-{result['summary']['removed_count']}</div><div class="stat-label">移除藥物</div></div>
        <div class="stat"><div class="stat-num modified">{result['summary']['modified_count']}</div><div class="stat-label">修改藥物</div></div>
        <div class="stat"><div class="stat-num unchanged">{result['summary']['unchanged_count']}</div><div class="stat-label">未變更</div></div>
    </div>
</div>
"""

    # Added drugs
    if result['added']:
        html += '<h2 class="added">+ 新增藥物</h2>\n<div class="drug-list">\n'
        for drug in result['added']:
            html += f'<div class="drug-item drug-added">+ {drug}</div>\n'
        html += '</div>\n'

    # Removed drugs
    if result['removed']:
        html += '<h2 class="removed">- 移除藥物</h2>\n<div class="drug-list">\n'
        for drug in result['removed']:
            html += f'<div class="drug-item drug-removed">- {drug}</div>\n'
        html += '</div>\n'

    # Modified drugs
    if result['modified']:
        html += '<h2 class="modified">~ 修改藥物</h2>\n'
        for mod in result['modified']:
            html += f"""<div class="diff-block">
<div class="diff-header">
    {mod['drug']}
    <span class="badge badge-added">+{mod['added_lines']}</span>
    <span class="badge badge-removed">-{mod['removed_lines']}</span>
    (相似度: {mod['similarity']:.1%})
</div>
"""
            for diff_type, line in mod['diff']:
                escaped = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                if diff_type == 'added':
                    html += f'<div class="diff-line line-added">+ {escaped}</div>\n'
                elif diff_type == 'removed':
                    html += f'<div class="diff-line line-removed">- {escaped}</div>\n'
                else:
                    html += f'<div class="diff-line line-equal">  {escaped}</div>\n'
            html += '</div>\n'

    html += '</div>\n</body>\n</html>'
    return html


def print_console_diff(result: dict):
    """在終端顯示差異"""
    s = result['summary']
    print(f"\n{'='*70}")
    print("版本差異摘要")
    print(f"{'='*70}")
    print(f"  舊版: {result['old_file']} ({result['old_drug_sections']} 藥物章節)")
    print(f"  新版: {result['new_file']} ({result['new_drug_sections']} 藥物章節)")
    print(f"\n  新增: +{s['added_count']}  移除: -{s['removed_count']}  修改: {s['modified_count']}  未變: {s['unchanged_count']}")

    if result['added']:
        print(f"\n--- 新增藥物 (+{len(result['added'])}) ---")
        for drug in result['added']:
            print(f"  + {drug}")

    if result['removed']:
        print(f"\n--- 移除藥物 (-{len(result['removed'])}) ---")
        for drug in result['removed']:
            print(f"  - {drug}")

    if result['modified']:
        print(f"\n--- 修改藥物 ({len(result['modified'])}) ---")
        for mod in result['modified']:
            print(f"  ~ {mod['drug']}  (+{mod['added_lines']}/-{mod['removed_lines']}, 相似度 {mod['similarity']:.1%})")


def main():
    parser = argparse.ArgumentParser(description='NHI 給付規定版本比較工具')
    parser.add_argument('old_docx', help='舊版 DOCX 檔案')
    parser.add_argument('new_docx', help='新版 DOCX 檔案')
    parser.add_argument('-o', '--output', help='輸出 HTML 報告路徑')
    parser.add_argument('--json', action='store_true', help='輸出 JSON 格式')
    args = parser.parse_args()

    print("=" * 70)
    print("NHI 給付規定版本比較工具")
    print("=" * 70)

    result = compare_versions(args.old_docx, args.new_docx)
    print_console_diff(result)

    # HTML report
    output_path = args.output or f"version_diff_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    html = generate_html_report(result)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n[*] HTML 報告: {output_path}")

    # JSON output
    if args.json:
        json_path = output_path.replace('.html', '.json')
        # Remove diff details for JSON (too large)
        json_result = {k: v for k, v in result.items() if k != 'modified'}
        json_result['modified'] = [
            {k: v for k, v in m.items() if k != 'diff'}
            for m in result['modified']
        ]
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, ensure_ascii=False, indent=2)
        print(f"[*] JSON 輸出: {json_path}")

    print(f"\n{'='*70}")
    print("比較完成!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
