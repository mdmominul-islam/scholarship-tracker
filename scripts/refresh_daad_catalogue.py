#!/usr/bin/env python3
"""Refresh the DAAD International Programmes Master's catalogue.

The DAAD API is the source of the programme list. Course detail pages are read
for the application route and English-language evidence. Unclear requirements
are deliberately marked as not confirmed rather than guessed.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
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
DETAIL = BASE + "/deutschland/studienangebote/international-programmes/en/detail/{}/"
PAGE_SIZE = 500
WORKERS = 6
TIMEOUT = 35
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ScholarshipTracker/1.0; +https://mdmominul-islam.github.io/scholarship-tracker/)",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": RESULT_PAGE,
}

def get(url: str, *, params=None, headers=None):
    last = None
    for attempt in range(4):
        try:
            response = requests.get(url, params=params, headers=headers or HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(f"Could not fetch {url}: {last}")

def fetch_all_masters() -> list[dict]:
    all_courses: list[dict] = []
    offset = 0
    total = None
    while total is None or offset < total:
        params = {
            "q": "",
            "degree[]": "2",  # Master's programmes
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
        print(f"Fetched {min(offset, total)} / {total} DAAD Master's records", flush=True)
        if offset >= total:
            break
    # Keep the newest response's source order but remove duplicate IDs.
    seen, unique = set(), []
    for item in all_courses:
        key = str(item.get("id") or item.get("courseName") or item.get("name") or "")
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique

def text_of(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip() if node else ""

def first_value(item: dict, keys: tuple[str, ...], fallback=""):
    for key in keys:
        value = item.get(key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value if v)
        if value not in (None, "", []):
            return str(value)
    return fallback

def parse_detail(course: dict) -> dict:
    course_id = course.get("id")
    path = course.get("link") or (f"/deutschland/studienangebote/international-programmes/en/detail/{course_id}/" if course_id else "")
    detail_url = urljoin(BASE, path) if path else ""
    defaults = {
        "teachingLanguage": first_value(course, ("language", "courseLanguage", "languages", "lang"), "See DAAD detail page"),
        "languageRequirements": "Not listed on the DAAD detail page or page could not be read.",
        "applicationRoute": "Not listed on the DAAD detail page.",
        "vpd": "Not confirmed — check the university application page.",
        "ielts": "Not listed by DAAD — check the university application page.",
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
        for dt_node in soup.find_all("dt"):
            label = text_of(dt_node).lower()
            dd = dt_node.find_next_sibling("dd")
            value = text_of(dd)
            if not value:
                continue
            if "language requirement" in label or "language skills" in label or "english proficiency" in label:
                language_req = value
            elif ("language" in label and "requirement" not in label) and (not teaching_language or teaching_language == "See DAAD detail page"):
                teaching_language = value
            elif "submit application via" in label or "application method" in label or "application procedure" in label:
                application_route = value

        if not language_req:
            language_req = defaults["languageRequirements"]
        if not application_route:
            application_route = defaults["applicationRoute"]

        low_route = application_route.lower()
        low_text = full_text.lower()
        if "vpd" in low_route or "vorprüfungsdokumentation" in low_route:
            vpd = "VPD explicitly mentioned on DAAD page — check if required for your case."
        elif "uni-assist" in low_route or "uni assist" in low_route:
            vpd = "uni-assist listed by DAAD; check whether this course requires a VPD."
        elif "vpd" in low_text or "uni-assist" in low_text or "uni assist" in low_text:
            vpd = "uni-assist/VPD mentioned in course information; verify the exact route."
        else:
            vpd = "Not mentioned by DAAD — verify the university application route."

        lang_low = language_req.lower()
        if "ielts" in lang_low:
            ielts = language_req
        else:
            ielts = "No IELTS score listed in DAAD language field — check accepted alternatives with the university."

        moi_match = re.search(r".{0,100}(?:medium of instruction|moi|previous degree.{0,35}english|degree.{0,35}taught in english).{0,150}", full_text, re.I)
        if moi_match and re.search(r"accept|waiv|exempt|suffic|proof|certificate", moi_match.group(0), re.I) and not re.search(r"not accept|not sufficient|cannot|does not", moi_match.group(0), re.I):
            moi = "MOI / previous English-taught degree is mentioned; confirm the exact evidence accepted by the university."
        elif moi_match and re.search(r"not accept|not sufficient|cannot|does not", moi_match.group(0), re.I):
            moi = "DAAD page indicates MOI is not sufficient; check the university page for exemptions."
        else:
            moi = "Not confirmed by DAAD — do not assume an MOI certificate is accepted."

        external = ""
        for a in soup.find_all("a", href=True):
            label = text_of(a).lower()
            href = a.get("href", "")
            if href.startswith("http") and "daad.de" not in href and ("course website" in label or "programme website" in label or label == "website"):
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
    name = first_value(course, ("courseName", "name", "title"), "Programme name not supplied")
    university = first_value(course, ("academy", "institution", "university", "institutionName"), "University not supplied")
    city = first_value(course, ("city", "location"), "Not specified")
    language = detail.get("teachingLanguage") or "See DAAD detail page"
    return {
        "id": str(course.get("id") or ""),
        "university": university,
        "programme": name,
        "city": city,
        "language": language,
        "duration": first_value(course, ("programmeDuration", "duration"), "Check DAAD page"),
        "tuition": first_value(course, ("tuitionFees", "tuition", "fees"), "Check DAAD page"),
        "intake": first_value(course, ("beginning", "start", "intake"), "Check DAAD page"),
        "subject": first_value(course, ("subject", "subjectGroup", "fieldOfStudy", "field"), "Not specified"),
        "detailUrl": detail.get("detailUrl", ""),
        "daadUrl": detail.get("detailUrl", ""),
        "officialUniversityUrl": detail.get("officialUniversityUrl", ""),
        "applicationRoute": detail.get("applicationRoute", ""),
        "vpd": detail.get("vpd", "Not confirmed — check the university application page."),
        "ielts": detail.get("ielts", "Not listed by DAAD — check the university application page."),
        "moi": detail.get("moi", "Not confirmed — do not assume an MOI certificate is accepted."),
        "languageRequirements": detail.get("languageRequirements", ""),
        "detailStatus": detail.get("detailStatus", ""),
    }

def main():
    courses = fetch_all_masters()
    print(f"Fetched {len(courses)} unique Master's programmes. Reading detail pages...", flush=True)
    details = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(parse_detail, course): course for course in courses}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            course = futures[future]
            key = str(course.get("id") or course.get("courseName") or course.get("name") or index)
            try:
                details[key] = future.result()
            except Exception as exc:
                details[key] = {"detailStatus": f"Fetch failed: {type(exc).__name__}"}
            if index % 50 == 0 or index == len(courses):
                print(f"Read {index} / {len(courses)} detail pages", flush=True)

    programmes = []
    for course in courses:
        key = str(course.get("id") or course.get("courseName") or course.get("name") or "")
        programmes.append(normalize(course, details.get(key, {})))

    payload = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "DAAD International Programmes public Master's search API",
        "scope": "Master's degree programmes indexed in DAAD International Programmes; this is not every German degree programme.",
        "count": len(programmes),
        "detailFetched": sum(1 for p in programmes if p.get("detailStatus") == "Fetched"),
        "programmes": programmes,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(programmes)} programmes to {OUTPUT}", flush=True)

if __name__ == "__main__":
    main()
