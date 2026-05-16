-- DDL for prod.a_unit
CREATE TABLE prod.a_unit (
    au_id       SERIAL PRIMARY KEY,
    au_area     VARCHAR(100),
    au_name     VARCHAR(255) NOT NULL,
    au_topic    VARCHAR(255),
    au_level    CHAR(2),
    au_content  TEXT,
    last_updated TIMESTAMP NOT NULL DEFAULT NOW()
);
