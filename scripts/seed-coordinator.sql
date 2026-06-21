-- Run against auth_db after services start
-- psql postgresql://campushire:PASSWORD@localhost:5432/auth_db -f scripts/seed-coordinator.sql

INSERT INTO users (id, email, password_hash, role, is_active)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'coordinator@campus.edu',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.VTtYH8Kz8Kz8Ku',
    'coordinator',
    true
)
ON CONFLICT (email) DO NOTHING;

-- password: password123
