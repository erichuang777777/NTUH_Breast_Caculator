#!/usr/bin/env python3
"""Monthly rule-based check for the official NHI drug coverage PDF.

The workflow downloads the latest "最新版藥品給付規定內容(整份帶走)" PDF,
extracts page text, and matches each breast drug by rule-based search terms
derived from the local database. The generated snapshot is compared against a
committed baseline so we can detect whether an update changes the wording or
page placement of a drug rule.
"""

from __future__ import annotations

import argparse
import logging
import hashlib
import io
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "nhi_drug_coverage.db"
BASELINE_PATH = ROOT / "data" / "validation" / "coverage_pdf_snapshot.json"
SOURCE_PAGE_URL = "https://www.nhi.gov.tw/ch/np-2508-1.html"
OFFICIAL_PDF_URL = "https://www.nhi.gov.tw/ch/dl-61741-ef3fcae5171e405c9f1548463d6dc30c-1.pdf"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": SOURCE_PAGE_URL,
}
logging.getLogger("pypdf").setLevel(logging.ERROR)
logging.getLogger("pypdf._reader").setLevel(logging.ERROR)
DATE_TOKEN_RE = re.compile(r"^\d{2,3}[/-]\d{1,2}[/-]\d{1,2}$")
MEANINGFUL_CHAR_RE = re.compile(r"[a-z\u4e00-\u9fff]")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH, help="Committed baseline snapshot")
    parser.add_argument("--write-snapshot", type=Path, default=None, help="Write a snapshot and exit")
    parser.add_argument("--strict", action="store_true", help="Fail on detected changes")
    parser.add_argument("--timeout", type=int, default=90, help="HTTP timeout in seconds")
    return parser.parse_args()


def fetch_pdf_bytes(url: str, timeout: int) -> bytes:
    resp = requests.get(url, timeout=timeout, headers=HTTP_HEADERS)
    resp.raise_for_status()
    return resp.content


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\x00", "")
    text = re.sub(r"\s+", "", text)
    return text.lower()


def is_meaningful_term(term: str) -> bool:
    return bool(term) and bool(MEANINGFUL_CHAR_RE.search(term))


def clean_term(term: str) -> str | None:
    term = normalize_text(term)
    if not term:
        return None
    if DATE_TOKEN_RE.fullmatch(term):
        return None
    if term.isdigit():
        return None
    if not is_meaningful_term(term):
        return None
    return term


def split_terms(value: str | None) -> list[str]:
    if not value:
        return []
    parts = re.split(r"[\/,、;；|()\[\]{}<>]+", str(value))
    cleaned = []
    for part in parts:
        term = normalize_text(part)
        if term and term not in cleaned:
            cleaned.append(term)
    return cleaned


def split_rule_phrases(value: str | None) -> list[str]:
    if not value:
        return []
    text = str(value)
    text = re.sub(r"\(?\d{2,3}[/-]\d{1,2}[/-]\d{1,2}\)?", " ", text)
    parts = re.split(r"[\/,、;；。|()\[\]{}<>]+", text)
    cleaned = []
    for part in parts:
        term = clean_term(part)
        if not term:
            continue
        if len(term) < 4:
            continue
        if term not in cleaned:
            cleaned.append(term)
    return cleaned


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def load_breast_drugs(conn: sqlite3.Connection) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT d.id, d.generic_name, d.trade_names, d.indication, d.stage,
               cr.therapy_line, cr.prior_auth_required, cr.condition, cr.nhi_ref_number
        FROM drugs d
        LEFT JOIN coverage_rules cr
          ON cr.drug_id = d.id
        WHERE d.specialty_id = 'oncology_breast'
        ORDER BY d.id, cr.id
        """
    ).fetchall()

    drugs: dict[int, dict] = {}
    for row in rows:
        drug = drugs.setdefault(
            row["id"],
            {
                "id": row["id"],
                "generic_name": row["generic_name"],
                "trade_names": row["trade_names"],
                "indication": row["indication"],
                "stage": row["stage"],
                "therapy_line": row["therapy_line"],
                "prior_auth_required": row["prior_auth_required"],
                "condition_parts": [],
                "nhi_ref_numbers": [],
            },
        )
        if row["condition"]:
            drug["condition_parts"].append(str(row["condition"]))
        if row["nhi_ref_number"]:
            drug["nhi_ref_numbers"].append(str(row["nhi_ref_number"]))
        if drug["therapy_line"] is None and row["therapy_line"] is not None:
            drug["therapy_line"] = row["therapy_line"]
        if drug["prior_auth_required"] is None and row["prior_auth_required"] is not None:
            drug["prior_auth_required"] = row["prior_auth_required"]

    return list(drugs.values())


def build_search_profile(drug: dict) -> dict:
    weights: dict[str, int] = {}
    primary_terms: set[str] = set()

    for term in split_terms(drug.get("generic_name")):
        weights[term] = max(weights.get(term, 0), 8)
        primary_terms.add(term)
    for term in split_terms(drug.get("trade_names")):
        weights[term] = max(weights.get(term, 0), 6)
        primary_terms.add(term)

    # Keep non-date reference fragments only when they look meaningful enough to help disambiguation.
    for ref in drug.get("nhi_ref_numbers") or []:
        ref_term = clean_term(ref)
        if ref_term and not DATE_TOKEN_RE.fullmatch(ref_term):
            weights[ref_term] = max(weights.get(ref_term, 0), 3)

    for part in drug.get("condition_parts", []):
        for term in split_rule_phrases(part):
            weights[term] = max(weights.get(term, 0), 4)

    for term in split_rule_phrases(drug.get("indication")):
        weights[term] = max(weights.get(term, 0), 2)

    return {
        "terms": weights,
        "primary_terms": sorted(primary_terms),
    }


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def build_page_hashes(pages: list[str]) -> list[str]:
    return [sha1_text(normalize_text(page)) for page in pages]


def score_drug_pages(pages: list[str], profile: dict, min_score: int = 8) -> list[dict]:
    normalized_pages = [normalize_text(page) for page in pages]
    weights: dict[str, int] = profile["terms"]
    primary_terms: list[str] = profile["primary_terms"]
    results = []

    for idx, page_text in enumerate(normalized_pages, start=1):
        score = 0
        primary_score = 0
        matched_terms = []
        for term, weight in weights.items():
            if term and term in page_text:
                score += weight
                matched_terms.append(term)
                if term in primary_terms:
                    primary_score += weight
        if primary_score and score >= min_score:
            results.append(
                {
                    "page": idx,
                    "score": score,
                    "primary_score": primary_score,
                    "matched_terms": matched_terms,
                }
            )

    if results:
        return results

    # Fallback: if no page reaches the threshold, keep the best primary match only.
    best = None
    for idx, page_text in enumerate(normalized_pages, start=1):
        score = 0
        primary_score = 0
        matched_terms = []
        for term, weight in weights.items():
            if term and term in page_text:
                score += weight
                matched_terms.append(term)
                if term in primary_terms:
                    primary_score += weight
        if primary_score:
            candidate = {
                "page": idx,
                "score": score,
                "primary_score": primary_score,
                "matched_terms": matched_terms,
            }
            if best is None or candidate["score"] > best["score"]:
                best = candidate
    return [best] if best else []


def snippet_for_page(page_text: str, terms: list[str], width: int = 220) -> str:
    normalized = normalize_text(page_text)
    best_idx = None
    best_term = None
    for term in terms:
        idx = normalized.find(term)
        if idx != -1 and (best_idx is None or idx < best_idx):
            best_idx = idx
            best_term = term
    if best_idx is None:
        return ""
    start = max(0, best_idx - width // 2)
    end = min(len(normalized), best_idx + len(best_term or "") + width // 2)
    return normalized[start:end]


def build_snapshot(pdf_url: str, source_page_url: str, pdf_bytes: bytes, pages: list[str], drugs: list[dict]) -> dict:
    page_hashes = build_page_hashes(pages)
    utc_now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    snapshot = {
        "source_page_url": source_page_url,
        "pdf_url": pdf_url,
        "pdf_sha256": sha256_bytes(pdf_bytes),
        "fetched_at": utc_now,
        "page_count": len(pages),
        "drugs": {},
    }
    for drug in drugs:
        profile = build_search_profile(drug)
        terms = list(profile["terms"].keys())
        matched_pages = score_drug_pages(pages, profile)
        page_info = []
        for match in matched_pages:
            page_no = match["page"]
            page_text = pages[page_no - 1]
            page_info.append({
                "page": page_no,
                "hash": page_hashes[page_no - 1],
                "snippet": snippet_for_page(page_text, terms),
                "score": match["score"],
                "matched_terms": match["matched_terms"],
            })
        snapshot["drugs"][str(drug["id"])] = {
            "drug_id": drug["id"],
            "generic_name": drug["generic_name"],
            "trade_names": drug["trade_names"],
            "terms": terms,
            "therapy_line": drug["therapy_line"],
            "prior_auth_required": drug["prior_auth_required"],
            "nhi_ref_numbers": drug["nhi_ref_numbers"],
            "matches": page_info,
        }
    return snapshot


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compare_snapshots(baseline: dict | None, current: dict) -> list[str]:
    if not baseline:
        return ["No baseline snapshot found."]

    issues = []
    if baseline.get("pdf_sha256") != current.get("pdf_sha256"):
        issues.append("Official PDF hash changed.")
    if baseline.get("page_count") != current.get("page_count"):
        issues.append(f"Page count changed: {baseline.get('page_count')} -> {current.get('page_count')}")

    base_drugs = baseline.get("drugs", {})
    cur_drugs = current.get("drugs", {})
    for drug_id, cur in cur_drugs.items():
        base = base_drugs.get(drug_id)
        if not base:
            issues.append(f"New drug entry in snapshot: {cur.get('generic_name')} ({drug_id})")
            continue
        base_pages = [m.get("page") for m in base.get("matches", [])]
        cur_pages = [m.get("page") for m in cur.get("matches", [])]
        if base_pages != cur_pages:
            issues.append(
                f"{cur.get('generic_name')} pages changed: {base_pages or ['-']} -> {cur_pages or ['-']}"
            )
            continue
        base_hashes = [m.get("hash") for m in base.get("matches", [])]
        cur_hashes = [m.get("hash") for m in cur.get("matches", [])]
        if base_hashes != cur_hashes:
            issues.append(f"{cur.get('generic_name')} matched page text changed on pages {cur_pages}")

    return issues


def print_report(snapshot: dict, issues: list[str]):
    print(f"Source page: {snapshot['source_page_url']}")
    print(f"PDF URL: {snapshot['pdf_url']}")
    print(f"PDF SHA256: {snapshot['pdf_sha256']}")
    print(f"Page count: {snapshot['page_count']}")
    print(f"Breast drugs tracked: {len(snapshot['drugs'])}")
    if not issues:
        print("[OK] No PDF coverage-rule drift detected")
    else:
        print("[WARN] Coverage PDF drift detected:")
        for item in issues:
            print(f"  - {item}")
    for drug in snapshot["drugs"].values():
        pages = ",".join(f"{m['page']}({m.get('score', 0)})" for m in drug["matches"]) or "-"
        print(f"{drug['drug_id']:>4} {drug['generic_name']:<28} pages={pages}")


def main() -> int:
    args = parse_args()
    conn = sqlite3.connect(DB_PATH)
    try:
        drugs = load_breast_drugs(conn)
    finally:
        conn.close()

    pdf_url = OFFICIAL_PDF_URL
    source_page_url = SOURCE_PAGE_URL
    pdf_bytes = fetch_pdf_bytes(pdf_url, args.timeout)
    pages = extract_pdf_pages(pdf_bytes)
    snapshot = build_snapshot(pdf_url, source_page_url, pdf_bytes, pages, drugs)

    if args.write_snapshot:
        save_json(args.write_snapshot, snapshot)
        print(f"[OK] wrote snapshot to {args.write_snapshot}")
        print_report(snapshot, [])
        return 0

    baseline = load_json(args.baseline)
    issues = compare_snapshots(baseline, snapshot)
    print_report(snapshot, issues if issues != ["No baseline snapshot found."] else [])

    if args.strict and issues:
        print(f"[FAIL] {len(issues)} coverage PDF change(s) detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
