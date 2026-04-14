"""LMS utilities for email parsing and work result processing."""

import html2text
import re
import logging
from models import UserWorks, MXWorks, EmailMessage
from db import db

logger = logging.getLogger(__name__)


def parse_email_content(subject, html_body):
    """Parse email subject and body to extract work result data."""
    txt = html2text.html2text(html_body)
    result = {}

    # Extract ID & user
    parts = subject.split("\"")
    if len(parts) > 3:
        extracted_id = parts[1]
        if extracted_id == "%TITLE%":
            result["id"] = "INVALID"
            return result
        result["id"] = extracted_id
        result["user"] = parts[3]
    else:
        result["id"] = "INVALID"
        return result

    incorrect_numbers = []

    for line in txt.splitlines():
        if line.startswith("Date/Time:"):
            result["time"] = line.replace("Date/Time:", "").strip()

        if line.startswith("Answered:"):
            raw_score = line.replace("Answered:", "").strip()
            clean_score = raw_score.replace("**", "").replace("|", "").strip()
            match = re.match(r'(\d+)\s*/\s*(\d+)', clean_score)
            result["score"] = f"{match.group(1)} out of {match.group(2)}" if match else clean_score

        if "Incorrect" in line:
            m = re.search(r'Question\s*(\d+)', line, re.IGNORECASE)
            if m:
                incorrect_numbers.append(m.group(1))

    result["incorrect"] = "All correct!" if not incorrect_numbers else "Q: " + ", ".join(incorrect_numbers)
    return result


def update_work_with_result(result):
    """Update user work record with email parsed result."""
    if "user" not in result:
        logger.warning(f"Missing 'user' in result: {result}")
        return

    if "id" not in result:
        logger.warning(f"Missing 'id' in result: {result}")
        return

    if result["id"] == "INVALID":
        logger.warning(f"Result 'id' is INVALID: {result}")
        return

    work_id_value = result["id"]

    # UserWorks.work_id is int in database, so always use int for query
    if str(work_id_value).isdigit():
        work_id_int = int(work_id_value)
    else:
        mx_work = MXWorks.query.filter_by(old_work_id=work_id_value).first()
        if not mx_work:
            logger.warning(f"No matching work_id found for old_work_id={work_id_value}")
            return
        work_id_int = mx_work.work_id

    updated_rows = UserWorks.query.filter(
        UserWorks.username == result["user"],
        UserWorks.work_id == work_id_int
    ).all()

    if not updated_rows:
        logger.warning(f"No matching work found for user={result['user']} id={work_id_int}")
        return

    for row in updated_rows:
        row.work_status = "Done"
        row.work_score = result.get("score")

        incorrect_value = result.get("incorrect", "")
        if incorrect_value and len(incorrect_value) > 100:
            incorrect_value = incorrect_value[:97] + "..."
        row.incorrect = incorrect_value

    db.session.commit()
    logger.warning(f"Updated {len(updated_rows)} rows with result={result}")
