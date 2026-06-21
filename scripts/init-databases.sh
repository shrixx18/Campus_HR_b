#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    SELECT 'CREATE DATABASE auth_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db')\gexec
    SELECT 'CREATE DATABASE opportunity_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'opportunity_db')\gexec
    SELECT 'CREATE DATABASE application_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'application_db')\gexec
    SELECT 'CREATE DATABASE communications_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'communications_db')\gexec
EOSQL
