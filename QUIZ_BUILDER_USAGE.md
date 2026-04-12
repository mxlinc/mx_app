# MCQ Quiz Builder - Usage Guide

## Getting Started

Access the quiz builder at: `/quiz/builder`

## Builder Interface

### Top Navigation Bar
- **Save** - Save question to database and go to full-screen preview
- **Preview** - Preview question in modal (doesn't save)
- **JSON** - Show question JSON structure in modal
- **Discard** - Clear form but keep Topic/Subtopic/Level

### Form Fields

#### Required Metadata (persists between questions)
- **Topic** - Select from: Number Sense, Algebra, Measurement, Data Management
- **Subtopic** - Select from: Fraction, Decimal, Percent, Ratio
- **Level** - Select from: D, E, F, G

#### Question Setup
- **Question Text** - Enter in LaTeX format (e.g., `$\frac{3}{4}$`)
- **Optional Image** - Upload or paste from clipboard
- **Options** - One per line in LaTeX format
- **Shuffle** - Checkbox to randomize option order
- **Correct Option** - Specify which option is correct (leave blank for first option)

## Workflow

### Creating a New Question
1. Fill out Topic, Subtopic, Level
2. Enter question text in LaTeX
3. (Optional) Upload image
4. Enter options, one per line
5. Specify correct option or leave blank for first
6. Click **Save**

### After Saving
You'll be taken to the full-screen display showing:
- Question as the student will see it
- ID band at top with Question ID
- Three links: Edit, JSON, New

### Options from Display Page

#### Check Answer
1. Select an option
2. Click "Check Answer"
3. Get instant feedback (✓ Correct or ✗ Incorrect)

#### Edit
- Click **Edit** to return to builder with form prefilled
- Make changes and click Save to update

#### JSON
- Click **JSON** to see the complete question structure in a modal
- Shows how the question is stored

#### New
- Click **New** to create another question
- Topic, Subtopic, Level are preserved from previous question
- Form is blank and ready for new content

#### Discard
- Clear the current question without saving
- Keeps Topic, Subtopic, Level for next question

## LaTeX Formatting Examples

### Fractions
- Input: `$\frac{3}{4}$`
- Displays as: 3/4 with line separator

### Regular Text
- Input: `Circle with radius 5`
- Displays as: Circle with radius 5

### Mixed
- Input: `Find the area of a circle with radius $5$ cm`
- Displays with proper formatting

## Database Structure

Questions are stored in the `q_bank` table:
- **id** - Unique question identifier (auto-generated)
- **type** - Question type (always 'mcq' for now)
- **topic** - Selected topic
- **subtopic** - Selected subtopic
- **level** - Difficulty level
- **json** - Complete question data including:
  - stem (question text)
  - input (options, shuffle setting)
  - answer (correct option info)
  - image (path to saved image if any)
- **created_at** - Timestamp
- **updated_at** - Last modification timestamp

## Images

- Images are saved to: `static/qimage/`
- File naming: `{question_id}.png`
- Max size: Recommended 5MB or less
- Formats: PNG, JPG supported

## Tips & Tricks

1. **Keyboard Shortcuts** - Coming soon
2. **Bulk Import** - Contact admin for batch question import
3. **LaTeX Help** - Use common fraction notation: `\frac{numerator}{denominator}`
4. **Quick Copy** - Use Copy option when creating similar questions (coming soon)

## Troubleshooting

### Question Not Saving
- Check that all required fields are filled
- Ensure at least one option is entered
- Check browser console for errors

### Image Not Displaying
- Verify file format (PNG/JPG)
- Check file size
- Try re-uploading

### LaTeX Not Rendering
- Verify LaTeX syntax is correct
- Check for matching brackets and braces
- Use $ for inline math: `$expression$`

## Other Question Types (Future)

- Multiple Response (MR)
- Hotspot
- Fill in Blank (FB)
- Multiple Fill in Blanks (MFB)

These will be added after MCQ is fully refined.
