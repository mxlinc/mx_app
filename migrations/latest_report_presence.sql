-- Latest Report presence storage. Run before deploying the new application code.
-- Uses APP_SCHEMA=prod; replace prod and ix_prod_ if deploying another schema.
BEGIN;

CREATE TABLE IF NOT EXISTS prod.student_presence (
    session_id VARCHAR(64) NOT NULL,
    user_id INTEGER NOT NULL,
    last_seen TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (session_id),
    FOREIGN KEY (user_id) REFERENCES prod.user_table (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_prod_student_presence_last_seen
    ON prod.student_presence (last_seen);

CREATE INDEX IF NOT EXISTS ix_prod_student_presence_user_id
    ON prod.student_presence (user_id);

COMMIT;
