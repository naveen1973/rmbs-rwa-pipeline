# ADR 0001 — Where ingestion happens & where data is transformed

**Status:** Accepted · **Date:** 2026-06-16 · **Context:** RMBS RWA pipeline (BigQuery warehouse)

This record exists to show that the ingestion trigger *and* the transformation layer
were chosen deliberately, with the alternatives weighed — not by default.

---

## Decision (summary)

1. **Ingest via a local CLI** (`prep_rmbs` + `load_bigquery`) for now — zero standing cloud cost.
   Keep the code import-friendly so it can later be wrapped in a Cloud Function (Option 2) with no rewrite.
2. **Transform inside BigQuery with SQL (ELT).** Python is reduced to *extract + decode*
   (flatten the `.xlsx`, decode EDW coded fields → typed staging). All analytical logic —
   banding, weighted averages, pool history, delinquency buckets, stratifications,
   period-on-period CPR/CDR — lives in **layered BigQuery SQL** (`staging → intermediate → marts`),
   plus a `controls` suite that reconciles against the investor report.
3. **Power Query stays thin** (connect + set types, no business logic).
   **DAX** is used only for slicer-reactive measures.

This satisfies two goals at once: it showcases SQL (project goal #2) and keeps cloud cost ≈ £0.

---

## Q1 — How does a new LLD tape get into BigQuery?

A raw EDW tape cannot load straight into BigQuery (multi-sheet `.xlsx`, header on row 2,
coded numeric fields). Something must flatten + decode it first. The three options differ
only in *where that step runs*.

### Option 1 — User runs a local command  ✅ chosen
- **Flow:** download LLD → `python -m src.ingest.prep_rmbs --deal X` (decode → CSVs) →
  `python -m src.warehouse.load_bigquery --deal X` (upload to staging) → SQL marts rebuild → Power BI refresh.
- **Infra:** none beyond Python + `gcloud auth`.
- **Pros:** simplest; zero standing cost; every step visible and debuggable locally;
  honest demonstration of the ETL engineering.
- **Cons:** self-serve only for a *technical* user (needs Python + repo).

### Option 2 — Upload to GCS → auto-ingest (Cloud Function)
- **Flow:** user drops `.xlsx` into a Cloud Storage bucket; the upload event triggers a
  Cloud Function running the same `prep_rmbs`/`load` code; marts rebuild automatically.
- **Infra:** GCS bucket, Cloud Function, event trigger, service account/IAM.
- **Pros:** genuinely self-serve for a *non-technical* user; best "product" story.
- **Cons:** real infra to build/secure/explain; logs in Cloud Logging not the terminal;
  small standing cost. **Deferred — this is the natural phase-2 upgrade of Option 1.**

### Option 3 — Manual upload via the BigQuery UI
- **Flow:** user loads a file through the BigQuery console; all transformation as SQL.
- **Catch:** the UI loads CSV/JSON/Parquet, **not** raw multi-sheet `.xlsx` — the user must
  pre-clean the tape in Excel every month.
- **Pros:** no Python step for the upload; all logic in SQL.
- **Cons:** pushes the hardest, most error-prone step (flattening/decoding) onto the user as a
  manual chore; fragile for raw EDW tapes. **Rejected** unless the source already arrives as clean CSV.

**Verdict:** Option 1 now; design the code so Option 2 is a thin wrapper, not a rewrite.

---

## Q2 — Where is data transformed? (BigQuery vs Power Query)

**Chosen: BigQuery SQL.** Rejected: transforming in Power Query.

| Reason | BigQuery SQL (chosen) | Power Query (rejected) |
|---|---|---|
| Single source of truth | Both consumers (Power BI **and** the HTML prototype) read identical marts | Only Power BI benefits; HTML dashboard drifts |
| Updating logic | Change one version-controlled `.sql` file; every refresh picks it up | Must open Power BI Desktop, edit M, republish |
| Performance / governance | Heavy lifting once, server-side, with documentable lineage | Re-runs every refresh; hard to test or diff |
| Showcases SQL (goal #2) | Yes — window functions, `QUALIFY`, `GROUPING SETS`, controls | No |

End-user experience becomes: **drop new LLD → BigQuery marts rebuild → click Refresh.**
No M editing, no `.pbix` surgery.

---

## Cost note

BigQuery on-demand free tier = **10 GB storage + 1 TB queries/month free**. This deal's data is
a few MB and queries scan kilobytes → effectively **£0**. Habits that keep it there *and* are good
practice: use `VIEW`s for transform layers (no storage), materialise only the small marts,
**partition** facts by `cutoff_date`, **cluster** by `deal`. Skipping the GCS landing bucket
(Option 2 infra) keeps standing cost at exactly zero.
