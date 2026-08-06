# Ingestion and clean-data contract

## Stable identity

`paper_id` is the normalized Crossref DOI: lowercase, trimmed, with any `doi:` or
`https://doi.org/` prefix removed. Records without a DOI are rejected, and the
first occurrence of a duplicate DOI is retained.

## Raw contract

The untouched Crossref response is written to `Paths.raw_api_response` before
parsing. Parsed `PaperRecord` objects are then written to
`Paths.raw_records_json`. Loading the parsed snapshot validates that it is a
list, that every object has all `PaperRecord` fields, and that `authors` and
`categories` are lists.

## Clean contract

Required fields are `paper_id`, `title`, `summary`, and a parseable publication
date. A row missing any of them is removed. Whitespace is normalized, dates are
stored as ISO `YYYY-MM-DD`, and duplicate `paper_id` values are removed.
Crossref/JATS markup and HTML entities are removed from title and summary before
they are handed to the index or test-set builders.

Authors and categories are normalized and deduplicated while preserving order.
Missing authors become `Unknown` in `authors_joined`; missing categories become
`Uncategorized` in `categories_joined` and `primary_category`.

Cleaning records its audit information in `DataFrame.attrs["cleaning_report"]`.
When `report_path` is supplied, the same payload is written as JSON with input,
output and filtered counts plus each rejected source index, paper ID and reason.
The supported reasons are `missing_paper_id`, `missing_title`,
`missing_summary`, `invalid_published`, and `duplicate_paper_id`.

`age_days` is the non-negative number of UTC calendar days from `published` to
the pipeline run date. `text_for_embedding` combines title, joined authors,
joined categories, publication date, and abstract with labeled lines.

## CP1 sample validation

Run from the project root with the virtual-environment interpreter:

```powershell
.\.venv\Scripts\python.exe -m ingestion.validation
```

The command parses `data/raw/crossref_sample.json`, checks the serialized raw
recovery boundary, writes sample CSV/JSON artifacts under `data/clean/`, and
validates null, duplicate, date, embedding-text, and `age_days` rules.
