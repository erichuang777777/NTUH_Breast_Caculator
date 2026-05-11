"""Shared calculation helpers for API endpoints.

These functions intentionally return JSON-serializable dictionaries and avoid
DOM/UI assumptions so they can be used by the local API server and tests.
"""

from __future__ import annotations

import math


def _num(value):
    try:
        if value is None or value == "":
            return None
        n = float(value)
        if math.isfinite(n):
            return n
    except Exception:
        return None
    return None


def _risk_class(pct, low=10, high=30):
    if pct < low:
        return "low"
    if pct < high:
        return "medium"
    return "high"


def _logistic(x):
    return 1 / (1 + math.exp(-x))


def calc_cts5(data):
    nodes = _num(data.get("nodes_pos", data.get("positive_nodes")))
    size_mm = _num(data.get("size_mm", data.get("tumor_size_mm")))
    grade = _num(data.get("grade"))
    age = _num(data.get("age"))
    if None in (nodes, size_mm, grade, age) or size_mm <= 0 or age <= 0:
        return None
    score = 0.438 * nodes + 0.988 * (0.093 * size_mm - 0.001 * size_mm * size_mm) + 0.375 * grade + 0.017 * age
    drr10 = (1 - math.exp(-0.00223 * math.exp(score))) * 100
    risk = "high" if score >= 3.86 else ("medium" if score >= 3.13 else "low")
    return {"score": score, "distant_recurrence_10y_pct": drr10, "risk": risk}


def calc_npi(data):
    size_mm = _num(data.get("size_mm", data.get("tumor_size_mm")))
    grade = _num(data.get("grade"))
    nodes = _num(data.get("nodes_pos", data.get("positive_nodes")))
    if None in (size_mm, grade, nodes) or size_mm <= 0:
        return None
    node_stage = 3 if nodes >= 4 else (2 if nodes >= 1 else 1)
    score = 0.2 * (size_mm / 10) + node_stage + grade
    if score <= 2.4:
        group, risk = "Excellent", "low"
    elif score <= 3.4:
        group, risk = "Good", "low"
    elif score <= 4.4:
        group, risk = "Moderate I", "medium"
    elif score <= 5.4:
        group, risk = "Moderate II", "medium"
    elif score <= 6.4:
        group, risk = "Poor", "high"
    else:
        group, risk = "Very Poor", "high"
    return {"score": score, "group": group, "risk": risk}


def calc_ihc4(data):
    er_h = _num(data.get("er_hscore"))
    pr_h = _num(data.get("pr_hscore"))
    ki67 = _num(data.get("ki67"))
    if None in (er_h, pr_h, ki67):
        return None
    her2 = 1 if data.get("her2") in ("+", "pos", 1, True) else 0
    score = 94.7 * (-0.100 * (er_h / 30) - 0.079 * (pr_h / 30) + 0.586 * her2 + 0.240 * math.log(1 + 10 * (ki67 / 100)))
    risk = "high" if score >= 25 else ("medium" if score >= 0 else "low")
    return {"score": score, "risk": risk}


def calc_magee(data):
    grade = _num(data.get("grade"))
    tubule = _num(data.get("tubule_score", 3))
    nuclear = _num(data.get("nuclear_score", grade))
    mitotic = _num(data.get("mitotic_score", grade))
    ns = _num(data.get("nottingham_score", None if None in (tubule, nuclear, mitotic) else tubule + nuclear + mitotic))
    size_mm = _num(data.get("size_mm", data.get("tumor_size_mm")))
    er_h = _num(data.get("er_hscore"))
    pr_h = _num(data.get("pr_hscore"))
    ki67 = _num(data.get("ki67"))
    if None in (ns, size_mm, er_h, pr_h, ki67):
        return None
    her2 = 1 if data.get("her2") in ("+", "pos", 1, True) else 0
    m1 = 15.31385 + ns * 1.4055 - er_h * 0.01924 - pr_h * 0.02925 + her2 * 11.99435 + size_mm * 0.0986
    m2 = 18.8042 + ns * 2.34123 - er_h * 0.03749 - pr_h * 0.03065 + her2 * 11.8378 + size_mm * 0.13838 + ki67 * 0.0035
    er_cat = 0 if er_h >= 200 else (1 if er_h >= 10 else 2)
    pr_cat = 0 if pr_h >= 200 else (1 if pr_h >= 10 else 2)
    her2_cat = 4 if her2 else 0
    ns_cat = 0 if ns <= 5 else (1 if ns <= 7 else 2)
    ki_cat = 0 if ki67 < 10 else (1 if ki67 < 20 else 2)
    size_cat = 0 if size_mm < 10 else (1 if size_mm < 20 else (2 if size_mm < 30 else 3))
    m3 = 13.424 + er_cat * 1.4 + pr_cat * 1.6 + her2_cat * 5 + ns_cat * 3 + ki_cat * 1.6 + size_cat * 0.5
    average = (m1 + m2 + m3) / 3
    risk = "high" if average >= 31 else ("medium" if average >= 18 else "low")
    return {"m1": m1, "m2": m2, "m3": m3, "average": average, "risk": risk}


def calc_rcb(data):
    d1 = _num(data.get("rcb_d1"))
    d2 = _num(data.get("rcb_d2"))
    finv_pct = _num(data.get("rcb_finv_pct"))
    ln = _num(data.get("rcb_ln_positive"))
    dmet = _num(data.get("rcb_largest_met_mm"))
    if None in (d1, d2, finv_pct, ln, dmet):
        return None
    finv = finv_pct / 100
    dprim = math.sqrt(max(d1, 0) * max(d2, 0))
    primary = 1.4 * math.pow(finv * dprim, 0.17) if dprim > 0 and finv > 0 else 0
    nodal = math.pow(4 * (1 - math.pow(0.75, ln)) * dmet, 0.17) if ln > 0 and dmet > 0 else 0
    score = primary + nodal
    if score == 0:
        group, risk = "RCB-0", "low"
    elif score <= 1.36:
        group, risk = "RCB-I", "low"
    elif score <= 3.28:
        group, risk = "RCB-II", "medium"
    else:
        group, risk = "RCB-III", "high"
    return {"score": score, "group": group, "risk": risk, "dprim": dprim, "primary_component": primary, "nodal_component": nodal}


def calc_non_sln(data):
    size_cm = _num(data.get("size_cm"))
    if size_cm is None:
        size_mm = _num(data.get("size_mm"))
        size_cm = None if size_mm is None else size_mm / 10
    positive = _num(data.get("positive_sln"))
    negative = _num(data.get("negative_sln"))
    if None in (size_cm, positive, negative):
        return None
    logit = 0.267 * size_cm + 1.443 * int(bool(data.get("multifocal"))) + 1.078 * int(bool(data.get("lvi"))) + 0.471 * positive - 0.618 * negative - 2.541
    risk_pct = _logistic(logit) * 100
    return {"logit": logit, "risk_pct": risk_pct, "risk": _risk_class(risk_pct, 10, 30)}


def ajcc_n_for_calc(n):
    if not n:
        return n
    n = str(n).replace("p", "", 1)
    return "N0" if n in ("N0i-", "N0i+") else n


def ajcc_anatomic(t, n, m):
    t = str(t or "").replace("p", "", 1)
    n = ajcc_n_for_calc(n)
    m = str(m or "").replace("p", "", 1)
    if not t or not n or not m:
        return None
    if m == "M1":
        return "IV"
    if t == "Tis":
        return "0" if n == "N0" else None
    ti = {"T1": 1, "T2": 2, "T3": 3, "T4": 4}.get(t)
    ni = {"N0": 0, "N1": 1, "N2": 2, "N3": 3}.get(n)
    if ti is None or ni is None or m != "M0":
        return None
    if ni == 3:
        return "IIIC"
    if ti == 4:
        return "IIIB" if ni <= 2 else "IIIC"
    if ni == 2:
        return "IIIA" if ti <= 3 else "IIIB"
    if ti == 3 and ni == 1:
        return "IIIA"
    if ti == 3 and ni == 0:
        return "IIB"
    if ti == 2 and ni == 1:
        return "IIB"
    if ti == 2 and ni == 0:
        return "IIA"
    if ti == 1 and ni == 1:
        return "IIA"
    if ti == 1 and ni == 0:
        return "IA"
    return None


def calculate_scores(data):
    scores = {
        "cts5": calc_cts5(data),
        "npi": calc_npi(data),
        "ihc4": calc_ihc4(data),
        "magee": calc_magee(data),
        "rcb": calc_rcb(data),
        "non_sln": calc_non_sln(data),
    }
    return {k: v for k, v in scores.items() if v is not None}


def staging_score(data):
    clinical = ajcc_anatomic(data.get("cT"), data.get("cN"), data.get("cM"))
    pathologic = ajcc_anatomic(data.get("pT"), data.get("pN"), data.get("pM"))
    return {
        "ajcc_v8": {
            "clinical": clinical,
            "pathologic": pathologic,
            "selected": pathologic or clinical,
            "selected_basis": "pathologic" if pathologic else ("clinical" if clinical else None),
        },
        "scores": calculate_scores(data),
    }
