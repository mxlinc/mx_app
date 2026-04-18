"""Question validators and schema validation utilities."""

from jsonschema import validate, ValidationError
from schemas import MCQ_SCHEMA


def validate_question_json(question_json, schema=None):
    """Validate question JSON against schema. Returns (valid, error_message)"""
    if schema is None:
        schema = MCQ_SCHEMA
    
    try:
        validate(instance=question_json, schema=schema)
        return True, None
    except ValidationError as e:
        error_msg = f"Schema Validation Error: {e.message}"
        if e.path:
            error_msg += f" at '{'.'.join(str(p) for p in e.path)}'"
        return False, error_msg


def order_question_json(question_json, field_order=None):
    """Reorder question JSON to match schema field order"""
    if field_order is None:
        field_order = ["id", "type", "stem", "image", "input", "answer", "topic", "subtopic", "level"]
    
    ordered = {}
    for field in field_order:
        if field in question_json:
            ordered[field] = question_json[field]
    
    # Special handling for stem to maintain field order
    if "stem" in ordered:
        stem_field_order = ["latex", "html", "feedback"]
        ordered_stem = {}
        for subfield in stem_field_order:
            if subfield in ordered["stem"]:
                ordered_stem[subfield] = ordered["stem"][subfield]
        ordered["stem"] = ordered_stem
    
    return ordered
