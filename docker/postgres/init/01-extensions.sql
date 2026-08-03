-- Runs once, when the data directory is first initialised.
--
-- Application tables are created by the backend entrypoint via
-- SQLAlchemy, so this file is reserved for database-level setup that
-- must exist before the application connects.

-- Case-insensitive text and trigram search, useful for the alert
-- message search the API exposes.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Record that initialisation ran, for support diagnostics.
DO $$
BEGIN
    RAISE NOTICE 'AI Warehouse Safety Inspector: database initialised.';
END
$$;
