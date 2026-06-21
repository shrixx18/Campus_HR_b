#!/usr/bin/env python3
"""Create coordinator user directly in auth_db."""

import os
import uuid

import psycopg2
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

COORDINATOR_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
EMAIL = "coordinator@campus.edu"
PASSWORD = "password123"

db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://campushire:change_me_strong_password@localhost:5432/auth_db",
)


def main():
    conn = psycopg2.connect(db_url.replace("postgresql+psycopg2", "postgresql"))
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (id, email, password_hash, role, is_active)
        VALUES (%s, %s, %s, 'coordinator', true)
        ON CONFLICT (email) DO NOTHING
        """,
        (str(COORDINATOR_ID), EMAIL, pwd.hash(PASSWORD)),
    )
    print(f"Coordinator ready: {EMAIL} / {PASSWORD}")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
