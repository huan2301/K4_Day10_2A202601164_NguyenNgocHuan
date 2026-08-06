from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from html import unescape
from pathlib import Path
import re
from typing import Any, Mapping

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


CROSSREF_WORKS_URL = "https://api.crossref.org/works"
_RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)
_TAG_PATTERN = re.compile(r"<[^>]+>")


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


def _text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return normalize_whitespace(unescape(_TAG_PATTERN.sub(" ", value)))


def _first_text(value: Any) -> str:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, list):
        for item in value:
            text = _text(item)
            if text:
                return text
    return ""


def _date_from_parts(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ""
    date_parts = value.get("date-parts")
    if not isinstance(date_parts, list) or not date_parts or not isinstance(date_parts[0], list):
        return ""
    parts = date_parts[0]
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day).isoformat()
    except (IndexError, TypeError, ValueError):
        return ""


def _published_date(item: Mapping[str, Any]) -> str:
    for key in ("published-print", "published-online", "published", "issued", "created", "indexed"):
        parsed = _date_from_parts(item.get(key))
        if parsed:
            return parsed
    return ""


def _updated_date(item: Mapping[str, Any]) -> str:
    for key in ("updated", "indexed", "created"):
        parsed = _date_from_parts(item.get(key))
        if parsed:
            return parsed
    return ""


def _authors(item: Mapping[str, Any]) -> list[str]:
    source = item.get("author", [])
    if not isinstance(source, list):
        return []
    authors: list[str] = []
    for author in source:
        if not isinstance(author, Mapping):
            continue
        name = _text(" ".join(part for part in (author.get("given"), author.get("family")) if isinstance(part, str)))
        name = name or _text(author.get("name")) or _text(author.get("literal"))
        if name and name not in authors:
            authors.append(name)
    return authors


def _categories(item: Mapping[str, Any]) -> list[str]:
    source = item.get("subject", [])
    if not isinstance(source, list):
        return []
    categories: list[str] = []
    for subject in source:
        normalized = _text(subject)
        if normalized and normalized not in categories:
            categories.append(normalized)
    return categories


def _urls(item: Mapping[str, Any]) -> tuple[str, str]:
    doi_url = _text(item.get("URL"))
    resource = item.get("resource")
    resource_url = ""
    if isinstance(resource, Mapping):
        primary = resource.get("primary")
        if isinstance(primary, Mapping):
            resource_url = _text(primary.get("URL"))
    pdf_url = ""
    links = item.get("link", [])
    if isinstance(links, list):
        for link in links:
            if not isinstance(link, Mapping):
                continue
            candidate = _text(link.get("URL"))
            content_type = _text(link.get("content-type")).lower()
            if candidate and (content_type == "application/pdf" or candidate.lower().endswith(".pdf")):
                pdf_url = candidate
                break
    return resource_url or doi_url, pdf_url


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Convert a Crossref works response into stable, clean ``PaperRecord`` objects."""
    if not isinstance(payload, Mapping):
        raise ValueError("Crossref payload must be a JSON object.")
    message = payload.get("message")
    if not isinstance(message, Mapping):
        raise ValueError("Crossref payload is missing its object-valued 'message' field.")
    items = message.get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref payload is missing its list-valued 'message.items' field.")

    records: list[PaperRecord] = []
    seen_ids: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            continue
        paper_id = _text(item.get("DOI")).lower()
        title = _first_text(item.get("title"))
        summary = _text(item.get("abstract"))
        published = _published_date(item)
        if not paper_id or not title or not summary or not published or paper_id in seen_ids:
            continue
        categories = _categories(item)
        abs_url, pdf_url = _urls(item)
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_updated_date(item),
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=_text(item.get("article-number")) or _text(item.get("publisher")),
            )
        )
        seen_ids.add(paper_id)
    return records


def _crossref_session() -> requests.Session:
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        status=4,
        backoff_factor=0.75,
        status_forcelist=_RETRYABLE_STATUS_CODES,
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"Accept": "application/json", "User-Agent": "day10-data-observability-lab/0.1"})
    return session


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch and persist Crossref source/raw records with retry-safe HTTP handling."""
    params = {"query": settings.source_query, "filter": settings.source_filter, "rows": settings.max_results}
    try:
        with _crossref_session() as session:
            response = session.get(CROSSREF_WORKS_URL, params=params, timeout=(5, 30))
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Crossref request failed after retries: {exc}") from exc
    try:
        payload = response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError("Crossref returned an invalid JSON response.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Crossref returned a JSON payload that is not an object.")

    write_json(settings.paths.raw_api_response, payload)
    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load a persisted raw-record snapshot and validate its schema."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Raw record snapshot must be a JSON list: {path}")
    field_names = set(PaperRecord.__dataclass_fields__)
    records: list[PaperRecord] = []
    for index, item in enumerate(payload):
        if not isinstance(item, Mapping):
            raise ValueError(f"Raw record at index {index} is not an object: {path}")
        missing = field_names - set(item)
        if missing:
            raise ValueError(f"Raw record at index {index} misses fields {sorted(missing)}: {path}")
        values = {name: item[name] for name in field_names}
        if not all(isinstance(values[name], str) for name in field_names - {"authors", "categories"}):
            raise ValueError(f"Raw record at index {index} contains invalid scalar fields: {path}")
        if not all(isinstance(values[name], list) and all(isinstance(v, str) for v in values[name]) for name in ("authors", "categories")):
            raise ValueError(f"Raw record at index {index} contains invalid list fields: {path}")
        records.append(PaperRecord(**values))
    return records
