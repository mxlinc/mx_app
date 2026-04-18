-- ============================================================
-- MONTESSORI SYSTEM DATABASE SETUP
-- Schema: prod
-- ============================================================

-- Create MUser table (Montessori students)
DROP TABLE IF EXISTS prod.muser CASCADE;
CREATE TABLE prod.muser (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    token VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drop and recreate MontessoriPackage table
DROP TABLE IF EXISTS prod.montessori_package CASCADE;
CREATE TABLE prod.montessori_package (
    id SERIAL PRIMARY KEY,
    subject VARCHAR(200) NOT NULL,
    topic VARCHAR(300) NOT NULL,
    work VARCHAR(300) NOT NULL,
    link TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- Create MUserPackage table (Assignments with tracking)
DROP TABLE IF EXISTS prod.muser_package CASCADE;
CREATE TABLE prod.muser_package (
    id SERIAL PRIMARY KEY,
    muser_id INTEGER NOT NULL REFERENCES prod.muser(id) ON DELETE CASCADE,
    package_id INTEGER NOT NULL REFERENCES prod.montessori_package(id) ON DELETE CASCADE,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    click_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP
);

-- Create Quiz table
DROP TABLE IF EXISTS prod.quiz CASCADE;
CREATE TABLE prod.quiz (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    topic VARCHAR(100),
    subtopic VARCHAR(100),
    question_ids VARCHAR(5000),  -- Comma-separated question IDs from q_bank
    question_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX idx_muser_token ON prod.muser(token);
CREATE INDEX idx_muser_package_student ON prod.muser_package(muser_id);
CREATE INDEX idx_muser_package_package ON prod.muser_package(package_id);
CREATE UNIQUE INDEX idx_muser_package_unique ON prod.muser_package(muser_id, package_id);
CREATE INDEX idx_quiz_topic ON prod.quiz(topic);

-- ============================================================
-- SAMPLE DATA (optional - remove if not needed)
-- ============================================================

-- Clear existing packages
DELETE FROM prod.montessori_package;

-- Insert 40 sample packages (20 Math + 20 English)
INSERT INTO prod.montessori_package (subject, topic, work, link) 
VALUES 
    -- MATHEMATICS (20 activities)
    ('Mathematics', 'Counting', 'Number Rods Activity', 'https://example.com/math/number-rods'),
    ('Mathematics', 'Counting', 'Golden Beads', 'https://example.com/math/golden-beads'),
    ('Mathematics', 'Counting', 'Spindle Boxes', 'https://example.com/math/spindle-boxes'),
    ('Mathematics', 'Numeration', 'Number Boards', 'https://example.com/math/number-boards'),
    ('Mathematics', 'Numeration', 'Colored Beads', 'https://example.com/math/colored-beads'),
    ('Mathematics', 'Operations', 'Addition Board', 'https://example.com/math/addition-board'),
    ('Mathematics', 'Operations', 'Subtraction Board', 'https://example.com/math/subtraction-board'),
    ('Mathematics', 'Operations', 'Multiplication Board', 'https://example.com/math/multiplication-board'),
    ('Mathematics', 'Operations', 'Division Board', 'https://example.com/math/division-board'),
    ('Mathematics', 'Fractions', 'Fraction Circles', 'https://example.com/math/fraction-circles'),
    ('Mathematics', 'Fractions', 'Fraction Bars', 'https://example.com/math/fraction-bars'),
    ('Mathematics', 'Geometry', 'Geometric Forms', 'https://example.com/math/geometric-forms'),
    ('Mathematics', 'Geometry', 'Solid Figures', 'https://example.com/math/solid-figures'),
    ('Mathematics', 'Geometry', 'Tessellations', 'https://example.com/math/tessellations'),
    ('Mathematics', 'Measurement', 'Pink Tower', 'https://example.com/math/pink-tower'),
    ('Mathematics', 'Measurement', 'Brown Stair', 'https://example.com/math/brown-stair'),
    ('Mathematics', 'Measurement', 'Red Rods', 'https://example.com/math/red-rods'),
    ('Mathematics', 'Patterns', 'Bead Chains', 'https://example.com/math/bead-chains'),
    ('Mathematics', 'Place Value', 'Decimal System', 'https://example.com/math/decimal-system'),
    ('Mathematics', 'Word Problems', 'Math Story Problems', 'https://example.com/math/story-problems'),
    
    -- ENGLISH (20 activities)
    ('English', 'Phonetics', 'Sandpaper Letters', 'https://example.com/english/sandpaper-letters'),
    ('English', 'Phonetics', 'Moveable Alphabet', 'https://example.com/english/moveable-alphabet'),
    ('English', 'Phonetics', 'Letter Sounds', 'https://example.com/english/letter-sounds'),
    ('English', 'Phonetics', 'Phonetic Reading', 'https://example.com/english/phonetic-reading'),
    ('English', 'Vocabulary', 'Object Box', 'https://example.com/english/object-box'),
    ('English', 'Vocabulary', 'Picture Cards', 'https://example.com/english/picture-cards'),
    ('English', 'Vocabulary', 'Classification Cards', 'https://example.com/english/classification-cards'),
    ('English', 'Word Building', 'Three-Letter Words', 'https://example.com/english/three-letter-words'),
    ('English', 'Word Building', 'Four-Letter Words', 'https://example.com/english/four-letter-words'),
    ('English', 'Word Building', 'Phonetic Words', 'https://example.com/english/phonetic-words'),
    ('English', 'Grammar', 'Parts of Speech', 'https://example.com/english/parts-of-speech'),
    ('English', 'Grammar', 'Verb Cards', 'https://example.com/english/verb-cards'),
    ('English', 'Grammar', 'Adjective Cards', 'https://example.com/english/adjective-cards'),
    ('English', 'Sentences', 'Sentence Building', 'https://example.com/english/sentence-building'),
    ('English', 'Sentences', 'Sentence Analysis', 'https://example.com/english/sentence-analysis'),
    ('English', 'Reading', 'Reading Stories', 'https://example.com/english/reading-stories'),
    ('English', 'Reading', 'Comprehension Cards', 'https://example.com/english/comprehension-cards'),
    ('English', 'Writing', 'Tracing Letters', 'https://example.com/english/tracing-letters'),
    ('English', 'Writing', 'Handwriting Practice', 'https://example.com/english/handwriting-practice'),
    ('English', 'Writing', 'Creative Writing', 'https://example.com/english/creative-writing');

-- Assign packages to students (first 3 students)
INSERT INTO prod.muser_package (muser_id, package_id, assigned_date) 
VALUES 
    (1, 1, CURRENT_TIMESTAMP),
    (1, 2, CURRENT_TIMESTAMP),
    (2, 3, CURRENT_TIMESTAMP),
    (2, 4, CURRENT_TIMESTAMP),
    (3, 5, CURRENT_TIMESTAMP);
