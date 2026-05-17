"""Database utility functions for Question Bank operations."""

from models import QBank
from db import db
from qb.handlers.common import generate_question_html as ensure_question_html, save_image_from_data_url
import logging

logger = logging.getLogger(__name__)


# ── Item-code helpers ──────────────────────────────────────────────────────────

def make_code(prefix: str, item_id: int, width: int = 4) -> str:
    """Format a numeric ID as a padded item code.  make_code('Q', 1) -> 'Q-0001'"""
    return f"{prefix}-{item_id:0{width}d}"


def code_to_id(code: str) -> int:
    """Extract numeric ID from an item code.  code_to_id('Q-0001') -> 1"""
    return int(code.split('-', 1)[1])


def quiz_code(quiz_id: int) -> str:
    """Return the standard quiz code for a quiz ID.  quiz_code(1) -> 'Q-0001'"""
    return make_code('Q', quiz_id)


def video_code(video_id: int) -> str:
    """Return the standard video code for a video ID.  video_code(3) -> 'V-0003'"""
    return make_code('V', video_id)


# ──────────────────────────────────────────────────────────────────────────────


def get_next_id():
    """
    Get the next ID for a question: max(id) + 1.
    Simple, predictable, and reusable.
    
    Returns:
        Next ID as integer
    """
    try:
        max_id_result = db.session.query(db.func.max(QBank.id)).scalar()
        max_id = max_id_result if max_id_result else 0
        return max_id + 1
    except Exception as e:
        logger.error(f"Failed to get next ID: {e}")
        return None


def rename_image_if_temp(image_path, new_id):
    """
    Rename image file from temp.png to use the question ID.
    
    Args:
        image_path: Current image path (e.g., './static/qimage/temp.png')
        new_id: The new question ID
    
    Returns:
        Updated image path or original path if rename failed
    """
    if not image_path or 'temp.png' not in image_path:
        return image_path
    
    try:
        from qb.handlers.common import rename_image_file
        new_filename = f"{new_id}.png"
        new_path = rename_image_file("temp.png", new_filename, subdir="qimage")
        return new_path if new_path else image_path
    except Exception as e:
        logger.warning(f"Failed to rename image file: {e}")
        return image_path


def save_question_to_db(question_type, topic, subtopic, level, final_json, data):
    """
    Shared image-handling and create/update dispatch used by all question handlers.
    Called after the handler has built final_json via prepare_html + order_json.
    Returns (question_object, error_message).
    """
    question_id = data.get('id')
    image_data_url = data.get('image_data_url')

    # Preserve existing image when editing without a new upload
    existing_image_path = None
    if question_id and not image_data_url:
        q = QBank.query.get(question_id)
        if q and q.json and 'image' in q.json:
            existing_image_path = q.json['image'].get('src')
            if existing_image_path:
                final_json['image'] = q.json['image']

    # For new questions get the ID upfront so the image can be named correctly
    new_question_id = get_next_id() if not question_id else None

    # Resolve image path
    image_path = None
    if image_data_url:
        img_id = question_id if question_id else new_question_id
        image_path = save_image_from_data_url(image_data_url, f"{img_id}.png", subdir="qimage")
        if image_path:
            if 'image' not in final_json:
                final_json['image'] = {"src": image_path, "alt": ""}
            else:
                final_json['image']['src'] = image_path
    elif existing_image_path:
        image_path = existing_image_path

    # Create or update
    if question_id:
        return update_question_safely(question_id, question_type, topic, subtopic, level, final_json, image_path)
    else:
        return create_question_safely(question_type, topic, subtopic, level, final_json, image_path, question_id=new_question_id)


def create_question_safely(question_type, topic, subtopic, level, question_json, image_path=None, question_id=None, retry_count=0):
    """
    Safely create a new question in the database with explicit ID assignment.
    
    Handles:
    - Explicit ID assignment (bypasses sequence)
    - Retry logic for rare collisions
    - Atomic transaction
    
    Args:
        question_type: 'mcq', 'mr', 'fill', 'ohs', etc.
        topic: Question topic
        subtopic: Question subtopic
        level: Difficulty level
        question_json: Complete question JSON (without ID)
        image_path: Optional image path (already named correctly)
        question_id: Optional pre-determined ID (e.g. when caller named the image file)
        retry_count: Internal retry counter (max 3)
    
    Returns:
        (question_object, error_message)
    """
    # Prevent infinite recursion
    if retry_count > 3:
        return None, "Failed to create question after 3 retry attempts due to ID collisions"
    
    try:
        # Use provided ID or generate next available
        next_id = question_id if question_id is not None else get_next_id()
        if next_id is None:
            return None, "Could not determine next ID"
        
        # Add ID to the JSON
        question_json['id'] = next_id
        
        # Update image src in JSON if provided
        if image_path and 'image' in question_json:
            question_json['image']['src'] = image_path
        
        # Generate HTML from LaTeX for all text fields (central conversion point)
        ensure_question_html(question_json)
        
        # Create the question with the explicit ID
        q = QBank(
            id=next_id,
            type=question_type,
            topic=topic,
            subtopic=subtopic,
            level=level,
            json=question_json
        )
        
        db.session.add(q)
        db.session.commit()
        
        logger.info(f"Created {question_type} question with ID {next_id}")
        return q, None
        
    except Exception as e:
        db.session.rollback()
        error_str = str(e).lower()
        
        # If it's a unique constraint violation (rare race condition), retry
        if "duplicate key" in error_str or "unique" in error_str:
            logger.warning(f"ID collision on retry {retry_count}, retrying...")
            return create_question_safely(question_type, topic, subtopic, level, question_json, image_path, question_id=None, retry_count=retry_count + 1)
        
        logger.exception(f"Failed to create question: {e}")
        return None, str(e)


def update_question_safely(question_id, question_type, topic, subtopic, level, question_json, image_path=None):
    """
    Safely update an existing question in the database.
    
    Args:
        question_id: ID of question to update
        question_type: 'mcq', 'mr', 'fill', 'ohs', etc.
        topic: Question topic
        subtopic: Question subtopic
        level: Difficulty level
        question_json: Complete question JSON
        image_path: Optional new image path
    
    Returns:
        (question_object, error_message)
    """
    try:
        q = QBank.query.get(question_id)
        if not q:
            return None, "Question not found"
        
        q.type = question_type
        q.topic = topic
        q.subtopic = subtopic
        q.level = level
        
        # Update image path if provided
        if image_path and 'image' in question_json:
            question_json['image']['src'] = image_path
        
        question_json['id'] = question_id
        
        # Generate HTML from LaTeX for all text fields (central conversion point)
        ensure_question_html(question_json)
        
        q.json = question_json
        
        db.session.commit()
        logger.info(f"Updated {question_type} question ID {question_id}")
        return q, None
        
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to update question: {e}")
        return None, str(e)
