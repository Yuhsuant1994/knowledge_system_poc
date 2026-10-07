
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user', 'dev', 'sales'))
);

INSERT INTO users (username, role) VALUES
    ('Hsuan AD', 'admin'),
    ('Hsuan US', 'user'),
    ('Hsuan DE', 'dev'),
    ('Hsuan SA', 'sales')
ON CONFLICT (username) DO NOTHING;


CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS hr_documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sales_readonly') THEN
        CREATE ROLE sales_readonly WITH LOGIN PASSWORD 'sales_readonly';
    END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO sales_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO sales_readonly;
REVOKE ALL ON hr_documents FROM sales_readonly;
