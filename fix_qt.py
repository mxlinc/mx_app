#!/usr/bin/env python3
# Fix question-templates.js by adding global assignment

with open(r'c:\Projects\mx_app\static\js\question-templates.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Add global assignment at the end if not already present
if 'window.QuestionTemplates' not in content:
    content += "\n\n// Ensure globally available\nif (typeof window !== 'undefined') { window.QuestionTemplates = QuestionTemplates; }\n"

# Write back
with open(r'c:\Projects\mx_app\static\js\question-templates.js', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)

print("File updated successfully")
print(f"File size: {len(content)} bytes")
