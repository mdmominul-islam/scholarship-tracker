#!/usr/bin/env python3
"""Import all DAAD International Programmes Bachelor and Master's listings.

The DAAD API provides the complete catalogue list. Course detail pages are
checked for VPD/application route and language evidence. Unknown requirements
remain explicitly unconfirmed; they are never inferred from teaching language.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "daad-programmes.json"
BASE = "https://www2.daad.de"
API = BASE + "/deutschland/studienangebote/international-programmes/api/solr/en/search.json"
RESULT_PAGE = BASE + "/deutschland/studienangebote/international-programmes/en/result/"
PAGE_SIZE = 500
WORKERS = 12
DETAILS_PER_DEGREE = 150
TIMEOUT = 15
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ScholarshipTracker/1.0; +https://mdmominul-islam.github.io/scholarship-tracker/)",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": RESULT_PAGE,
}
DEGREES = [(1, "Bachelor"), (2, "Master")]

def get(url: str, *, params=None, headers=None):
    last = None
    for attempt in range(2):
        try:
            response = requests.get(
                url, params=params, headers=headers or HEADERS,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            if attempt == 0:
                time.sleep(1.2)
    raise RuntimeError(f"Could not fetch {url}: {last}")

def fetch_degree(degree_id: int, degree_name: str) -> list[dict]:
    all_courses: list[dict] = []
    offset = 0
    total = None
    while total is None or offset < total:
        params = {
            "q": "",
            "degree[]": str(degree_id),
            "limit": str(PAGE_SIZE),
            "offset": str(offset),
            "display": "list",
            "sort": "4",
        }
        payload = get(API, params=params).json()
        courses = payload.get("courses") or []
        total = int(payload.get("numResults") or len(courses))
        if not courses:
            break
        all_courses.extend(courses)
        offset += len(courses)
        print(f"Fetched {min(offset, total)} / {total} DAAD {degree_name} listings", flush=True)
        if offset >= total:
            break
    seen, unique = set(), []
    for item in all_courses:
        key = str(item.get("id") or item.get("courseName") or item.get("name") or "")
        if key and key not in seen:
            seen.add(key)
            item["_degreeType"] = degree_name
            unique.append(item)
    return unique

def text_of(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""

def first_value(item: dict, keys: tuple[str, ...], fallback=""):
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            value = ", ".join(
                str(v.get("name") or v.get("label") or v) if isinstance(v, dict) else str(v)
                for v in value if v
            )
        if value not in (None, "", []):
            return str(value)
    return fallback

def parse_detail(course: dict) -> dict:
    course_id = course.get("id")
    path = course.get("link") or (
        f"/deutschland/studienangebote/international-programmes/en/detail/{course_id}/"
        if course_id else ""
    )
    detail_url = urljoin(BASE, path) if path else ""
    defaults = {
        "teachingLanguage": first_value(course, ("language", "courseLanguage", "languages", "lang"), "See DAAD detail page"),
        "languageRequirements": "Not listed by DAAD — check the university application page.",
        "applicationRoute": "Not listed by DAAD — check the university application page.",
        "vpd": "Not confirmed — check the university application page.",
        "ielts": "Not confirmed — check accepted English tests with the university.",
        "moi": "Not confirmed — do not assume an MOI certificate is accepted.",
        "officialUniversityUrl": "",
        "detailStatus": "Not fetched",
    }
    if not detail_url:
        return {**defaults, "detailUrl": ""}
    try:
        response = get(detail_url, headers={**HEADERS, "Accept": "text/html,application/xhtml+xml"})
        soup = BeautifulSoup(response.text, "html.parser")
        full_text = text_of(soup)
        language_req = ""
        application_route = ""
        teaching_language = defaults["teachingLanguage"]
        for node in soup.find_all("dt"):
            label = text_of(node).lower()
            dd = node.find_next_sibling("dd")
            value = text_of(dd)
            if not value:
                continue
            if any(k in label for k in ("language requirement", "language skills", "english proficiency")):
                language_req = value
            elif "language" in label and "requirement" not in label and teaching_language == "See DAAD detail page":
                teaching_language = value
            elif any(k in label for k in ("submit application via", "application method", "application procedure")):
                application_route = value

        if not language_req:
            language_req = defaults["languageRequirements"]
        if not application_route:
            application_route = defaults["applicationRoute"]

        low_route = application_route.lower()
        low_text = full_text.lower()
        if "vpd" in low_route or "vorprüfungsdokumentation" in low_route:
            vpd = "VPD explicitly mentioned by DAAD — verify whether required for your applicant category."
        elif "uni-assist" in low_route or "uni assist" in low_route:
            vpd = "uni-assist listed by DAAD — confirm whether a VPD is required."
        elif "vpd" in low_text or "uni-assist" in low_text or "uni assist" in low_text:
            vpd = "uni-assist/VPD mentioned — verify the exact application route."
        else:
            vpd = "Not confirmed by DAAD — check the university application page."

        if re.search(r"\bIELTS\b", language_req, re.I):
            ielts = language_req
        else:
            ielts = "No IELTS score specified in the DAAD language field — check accepted alternatives."

        moi_match = re.search(
            r".{0,120}(?:medium of instruction|\bMOI\b|previous degree.{0,40}English|degree.{0,40}taught in English).{0,180}",
            full_text, re.I
        )
        if moi_match and re.search(r"accept|waiv|exempt|suffic|proof|certificate", moi_match.group(0), re.I) and not re.search(r"not accept|not sufficient|cannot|does not", moi_match.group(0), re.I):
            moi = "MOI / previous English-taught degree is mentioned — confirm exact evidence with the university."
        elif moi_match and re.search(r"not accept|not sufficient|cannot|does not", moi_match.group(0), re.I):
            moi = "DAAD page indicates MOI may not be sufficient — check for university exemptions."
        else:
            moi = "Not confirmed by DAAD — do not assume an MOI certificate is accepted."

        external = ""
        for a in soup.find_all("a", href=True):
            label, href = text_of(a).lower(), a.get("href", "")
            if href.startswith("http") and "daad.de" not in href and (
                "course website" in label or "programme website" in label or label == "website"
            ):
                external = href
                break
        return {
            **defaults,
            "teachingLanguage": teaching_language or defaults["teachingLanguage"],
            "languageRequirements": language_req,
            "applicationRoute": application_route,
            "vpd": vpd,
            "ielts": ielts,
            "moi": moi,
            "officialUniversityUrl": external,
            "detailUrl": detail_url,
            "detailStatus": "Fetched",
        }
    except Exception as exc:
        return {**defaults, "detailUrl": detail_url, "detailStatus": f"Fetch failed: {type(exc).__name__}"}

def normalize(course: dict, detail: dict) -> dict:
    return {
        "id": str(course.get("id") or ""),
        "degreeType": course.get("_degreeType", "Unknown"),
        "university": first_value(course, ("academy", "institution", "university", "institutionName"), "University not supplied"),
        "programme": first_value(course, ("courseName", "name", "title"), "Programme name not supplied"),
        "city": first_value(course, ("city", "location"), "Not specified"),
        "language": detail.get("teachingLanguage") or first_value(course, ("language", "courseLanguage", "languages", "lang"), "See DAAD detail page"),
        "duration": first_value(course, ("programmeDuration", "duration"), "Check DAAD page"),
        "tuition": first_value(course, ("tuitionFees", "tuition", "fees", "costString"), "Check DAAD page"),
        "intake": first_value(course, ("beginning", "start", "intake"), "Check DAAD page"),
        "subject": first_value(course, ("subject", "subjectGroup", "fieldOfStudy", "field"), "Not specified"),
        "detailUrl": detail.get("detailUrl", ""),
        "daadUrl": detail.get("detailUrl", ""),
        "officialUniversityUrl": detail.get("officialUniversityUrl", ""),
        "applicationRoute": detail.get("applicationRoute", ""),
        "vpd": detail.get("vpd", "Not confirmed — check the university application page."),
        "ielts": detail.get("ielts", "Not confirmed — check accepted English tests with the university."),
        "moi": detail.get("moi", "Not confirmed — do not assume an MOI certificate is accepted."),
        "languageRequirements": detail.get("languageRequirements", ""),
        "detailStatus": detail.get("detailStatus", ""),
    }

def main():
    by_degree = {}
    for degree_id, degree_name in DEGREES:
        by_degree[degree_name] = fetch_degree(degree_id, degree_name)
    courses = by_degree["Bachelor"] + by_degree["Master"]
    print(
        f"Fetched {len(by_degree['Bachelor'])} Bachelor + {len(by_degree['Master'])} Master's listings. "
        "Reading DAAD detail pages...",
        flush=True
    )
    # Publish the complete programme list immediately. Detail-page enrichment
    # runs afterwards, so a slow DAAD detail server cannot leave the catalogue empty.
    initial_programmes = [normalize(course, {}) for course in courses]
    initial_counts = {
        "Bachelor": sum(1 for p in initial_programmes if p["degreeType"] == "Bachelor"),
        "Master": sum(1 for p in initial_programmes if p["degreeType"] == "Master"),
    }
    initial_payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "DAAD International Programmes public API",
        "scope": "All Bachelor and Master's listings returned by the DAAD International Programmes catalogue; not every degree programme offered in Germany.",
        "count": len(initial_programmes),
        "countsByDegree": initial_counts,
        "detailFetched": 0,
        "detailFailed": 0,
        "detailEnrichmentStatus": "In progress",
        "programmes": initial_programmes,
    }
    OUTPUT.write_text(json.dumps(initial_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Published full listing snapshot: {initial_counts['Bachelor']} Bachelor + "
        f"{initial_counts['Master']} Master's = {len(initial_programmes)} programmes.",
        flush=True
    )
    # Fetch complete degree listings first. Detail pages are slower and not all
    # DAAD entries expose the same fields, so enrich a representative recent
    # subset per degree; keep all remaining listings with honest "Not confirmed"
    # values rather than delaying or dropping the full catalogue.
    selected = []
    selected_ids = set()
    for degree_name in ("Bachelor", "Master"):
        group = [x for x in by_degree[degree_name]][:DETAILS_PER_DEGREE]
        selected.extend(group)
        selected_ids.update(
            f"{x.get('_degreeType','')}:{x.get('id') or x.get('courseName') or x.get('name') or ''}"
            for x in group
        )
    print(
        f"Enriching {len(selected)} course detail pages "
        f"({DETAILS_PER_DEGREE} per degree); all listings remain included.",
        flush=True
    )
    details = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {
            pool.submit(parse_detail, course): course
            for course in selected
        }
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            course = futures[future]
            key = f"{course.get('_degreeType','')}:{course.get('id') or course.get('courseName') or course.get('name') or index}"
            try:
                details[key] = future.result()
            except Exception as exc:
                details[key] = {"detailStatus": f"Fetch failed: {type(exc).__name__}"}
            if index % 50 == 0 or index == len(selected):
                print(f"Enriched {index} / {len(selected)} DAAD detail pages", flush=True)

    programmes = []
    for course in courses:
        key = f"{course.get('_degreeType','')}:{course.get('id') or course.get('courseName') or course.get('name') or ''}"
        programmes.append(normalize(course, details.get(key, {})))

    counts = {
        "Bachelor": sum(1 for p in programmes if p["degreeType"] == "Bachelor"),
        "Master": sum(1 for p in programmes if p["degreeType"] == "Master"),
    }
    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "DAAD International Programmes public API",
        "scope": "All Bachelor and Master's listings returned by the DAAD International Programmes catalogue; not every degree programme offered in Germany.",
        "count": len(programmes),
        "countsByDegree": counts,
        "detailFetched": sum(1 for p in programmes if p.get("detailStatus") == "Fetched"),
        "detailFailed": sum(1 for p in programmes if str(p.get("detailStatus","")).startswith("Fetch failed")),
        "detailEnrichmentStatus": "Complete",
        "programmes": programmes,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {counts['Bachelor']} Bachelor + {counts['Master']} Master's = {len(programmes)} total to {OUTPUT}", flush=True)

if __name__ == "__main__":
    main()
