import os, time
import psycopg
from psycopg.rows import dict_row

DSN = os.environ.get("DATABASE_URL", "postgresql://jobs:jobs@db:5432/jobs")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id text PRIMARY KEY,
  title text NOT NULL, company text NOT NULL DEFAULT '–',
  city text NOT NULL, lat double precision NOT NULL, lng double precision NOT NULL, country text NOT NULL,
  cat text NOT NULL, level text NOT NULL, mode text NOT NULL,
  salary text NOT NULL DEFAULT '', date text NOT NULL DEFAULT '', url text NOT NULL DEFAULT '',
  source text NOT NULL DEFAULT '', custom boolean NOT NULL DEFAULT false,
  first_seen timestamptz NOT NULL DEFAULT now(), last_seen timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS status (
  job_id text PRIMARY KEY, status text NOT NULL, updated timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS meta (key text PRIMARY KEY, value jsonb NOT NULL);
"""


def conn():
    return psycopg.connect(DSN, row_factory=dict_row, autocommit=True)


def init(retries=30):
    for i in range(retries):
        try:
            with conn() as c:
                c.execute(SCHEMA)
            return
        except psycopg.OperationalError:
            if i == retries - 1:
                raise
            time.sleep(2)
