"""Load capital structure (tranche) data to BigQuery dim_tranche table."""

import csv
from pathlib import Path
from google.cloud import bigquery

PROJECT = "rmbs-rwa-pipeline"
DATASET = "rmbs_mart"
TABLE = "dim_tranche"

CSV_PATH = Path(__file__).parent.parent / "config" / "capital_structures.csv"

SCHEMA = [
    bigquery.SchemaField("deal_id", "STRING"),
    bigquery.SchemaField("tranche_id", "STRING"),
    bigquery.SchemaField("isin", "STRING"),
    bigquery.SchemaField("original_balance", "NUMERIC"),
    bigquery.SchemaField("current_balance", "NUMERIC"),
    bigquery.SchemaField("factor", "FLOAT64"),
    bigquery.SchemaField("attachment", "FLOAT64"),
    bigquery.SchemaField("detachment", "FLOAT64"),
    bigquery.SchemaField("credit_enhancement", "FLOAT64"),
    bigquery.SchemaField("coupon", "STRING"),
    bigquery.SchemaField("maturity_date", "DATE"),
    bigquery.SchemaField("cutoff_date", "DATE"),
]


def load_tranches():
    client = bigquery.Client(project=PROJECT)
    table_ref = f"{PROJECT}.{DATASET}.{TABLE}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMA,
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    with open(CSV_PATH, "rb") as f:
        job = client.load_table_from_file(f, table_ref, job_config=job_config)

    job.result()
    table = client.get_table(table_ref)
    print(f"Loaded {table.num_rows} rows to {table_ref}")


if __name__ == "__main__":
    load_tranches()
