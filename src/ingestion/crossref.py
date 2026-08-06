from __future__ import annotations

from datetime import datetime
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
import re
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _first(value: Any, default: Any = "") -> Any:
    if isinstance(value, list):
        return value[0] if value else default
    return value if value is not None else default


def _crossref_date(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        block = item.get(key)
        if not isinstance(block, dict):
            continue
        parts = _first(block.get("date-parts"), [])
        if not isinstance(parts, (list, tuple)) or not parts:
            continue
        padded = (list(parts) + [1, 1])[:3]
        try:
            return datetime(*map(int, padded)).date().isoformat()
        except (TypeError, ValueError):
            continue
    return ""


def _normalize_doi(value: Any) -> str:
    doi = normalize_whitespace(str(value or "")).lower()
    doi = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", doi)
    return doi.strip()


def _strip_markup(value: Any) -> str:
    return normalize_whitespace(re.sub(r"<[^>]+>", " ", unescape(str(value or ""))))


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse a Crossref works payload into DOI-keyed ``PaperRecord`` objects.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    records: list[PaperRecord] = []
    seen: set[str] = set()
    items = payload.get("message", {}).get("items", [])
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        doi = _normalize_doi(item.get("DOI"))
        title = _strip_markup(_first(item.get("title")))
        if not doi or not title or doi in seen:
            continue
        abstract = _strip_markup(item.get("abstract"))
        authors = []
        for author in item.get("author", []) or []:
            name = normalize_whitespace(" ".join(filter(None, [author.get("given"), author.get("family")])))
            if name:
                authors.append(name)
        categories = [normalize_whitespace(str(value)) for value in (item.get("subject") or [])]
        categories = list(dict.fromkeys(value for value in categories if value))
        links = item.get("link") or []
        pdf_url = next(
            (str(link.get("URL", "")) for link in links if "pdf" in str(link.get("content-type", "")).lower()),
            "",
        )
        published = _crossref_date(item, "published", "published-online", "published-print", "issued")
        updated = _crossref_date(item, "indexed", "deposited") or published
        records.append(PaperRecord(
            paper_id=doi,
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=categories[0] if categories else "Uncategorized",
            published=published,
            updated=updated,
            abs_url=normalize_whitespace(str(item.get("URL") or f"https://doi.org/{doi}")),
            pdf_url=normalize_whitespace(pdf_url),
            comment=normalize_whitespace(str(item.get("publisher", ""))),
        ))
        seen.add(doi)
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch Crossref records and persist both response and parsed snapshots.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": "DOI,title,abstract,author,subject,published,issued,created,indexed,deposited,URL,link,publisher",
    }
    retry = Retry(
        total=4,
        backoff_factor=1.0,
        status_forcelist=(429, 503),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    response = session.get(
        "https://api.crossref.org/works",
        params=params,
        headers={"User-Agent": "day10-data-observability-lab/0.1 (mailto:student@example.com)"},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    if not records:
        raise RuntimeError("Crossref returned no usable records.")
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load and validate a parsed ``PaperRecord`` JSON snapshot."""
    if not path.exists():
        raise FileNotFoundError(f"Raw record snapshot does not exist: {path}")
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of raw records in {path}.")
    records: list[PaperRecord] = []
    expected = set(PaperRecord.__dataclass_fields__)
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Raw record {index} must be an object.")
        missing = expected - set(item)
        if missing:
            raise ValueError(f"Raw record {index} is missing fields: {sorted(missing)}")
        values = {key: item[key] for key in expected}
        if not isinstance(values["authors"], list) or not isinstance(values["categories"], list):
            raise ValueError(f"Raw record {index} authors/categories must be lists.")
        records.append(PaperRecord(**values))
    return records
