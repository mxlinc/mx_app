-- DDL for prod.interactions
-- Sequence starts at 1049 so interaction codes begin at I-1049

CREATE SEQUENCE prod.interactions_code_seq START WITH 1049;

CREATE TABLE prod.interactions (
    id           SERIAL PRIMARY KEY,
    lesson_code  TEXT NOT NULL,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW(),
    file_name    VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    broad_area   VARCHAR(100),
    details      TEXT
);

-- Add the DEFAULT separately so the sequence is guaranteed to exist first
ALTER TABLE prod.interactions
    ALTER COLUMN lesson_code SET DEFAULT ('I-' || lpad(nextval('prod.interactions_code_seq')::text, 4, '0'::text));
