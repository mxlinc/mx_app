"""
Standalone script to load questions from JSON file and insert into q_bank table.
"""

import os
import json
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env file")

# Convert postgres:// to postgresql+psycopg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Schema
SCHEMA = os.getenv("APP_SCHEMA", "prod")

# JSON file path
JSON_FILE_PATH = r"C:\Projects\mx_app\questions.json"

# Hard-coded values
TOPIC = "Algebra"
SUBTOPIC = "Review"
LEVEL = "I"


def load_and_insert_questions():
    """Load questions from JSON file and insert into database."""
    
    # Create engine and session
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Read JSON file
        print(f"Reading JSON file: {JSON_FILE_PATH}")
        if not os.path.exists(JSON_FILE_PATH):
            raise FileNotFoundError(f"JSON file not found: {JSON_FILE_PATH}")
        
        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse JSON, with fallback to fix common issues
        try:
            questions = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parse error: {e}")
            print("Attempting to fix incomplete JSON...")
            
            # Fix incomplete JSON by removing trailing comma and closing array
            content = content.rstrip()
            if content.endswith(','):
                content = content[:-1]
            if not content.rstrip().endswith(']'):
                content = content + '\n]'
            
            try:
                questions = json.loads(content)
                print("✓ Fixed JSON successfully")
            except json.JSONDecodeError as e2:
                raise ValueError(f"Could not fix JSON: {e2}")
        
        if not isinstance(questions, list):
            raise ValueError("JSON file must contain an array of questions")
        
        print(f"Found {len(questions)} questions to insert")
        
        # Get the current max ID to generate new IDs
        result = session.execute(
            text(f"SELECT MAX(id) FROM {SCHEMA}.q_bank")
        )
        max_id = result.scalar()
        next_id = (max_id or 0) + 1
        
        # Insert each question
        inserted_count = 0
        for idx, question in enumerate(questions, 1):
            try:
                # Generate new ID and update JSON
                question_id = next_id + idx - 1
                question['id'] = str(question_id)
                
                # Extract type from JSON
                q_type = question.get('type', 'unknown')
                
                # Prepare SQL insert
                insert_sql = text(f"""
                    INSERT INTO {SCHEMA}.q_bank (id, type, json, topic, subtopic, level)
                    VALUES (:id, :type, :json, :topic, :subtopic, :level)
                """)
                
                session.execute(insert_sql, {
                    'id': question_id,
                    'type': q_type,
                    'json': json.dumps(question),
                    'topic': TOPIC,
                    'subtopic': SUBTOPIC,
                    'level': LEVEL
                })
                
                inserted_count += 1
                print(f"  ✓ Question {idx}: ID={question_id}, Type={q_type}")
                
            except Exception as e:
                print(f"  ✗ Question {idx} failed: {str(e)}")
                session.rollback()
                raise
        
        # Commit all changes
        session.commit()
        print(f"\n✅ Successfully inserted {inserted_count} questions into {SCHEMA}.q_bank")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Question Loader Script")
    print("=" * 60)
    print(f"Database Schema: {SCHEMA}")
    print(f"Topic: {TOPIC}")
    print(f"Subtopic: {SUBTOPIC}")
    print(f"Level: {LEVEL}")
    print("=" * 60)
    
    load_and_insert_questions()
