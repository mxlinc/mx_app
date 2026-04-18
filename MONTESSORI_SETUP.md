# Montessori System Setup Guide

## Overview
The Montessori Materials system is a **completely separate subsystem** from the LMS and Quiz Builder. It allows admins to:
1. Create and manage Montessori students (independent of LMS users)
2. Create and assign learning packages to students
3. Track engagement (click counts and access dates)
4. Share public links with parents/students that require no login

## Architecture

### Database Tables
Three new tables in your schema:

1. **muser** - Montessori students
   - `id` - Primary key
   - `name` - Student name
   - `token` - Unique access token (auto-generated)
   - `created_at` - Creation timestamp

2. **montessori_package** - Learning material packages
   - `id` - Primary key
   - `title` - Package title
   - `description` - Package description
   - `link` - URL to the learning material
   - `created_at`, `updated_at` - Timestamps
   - `is_deleted` - Soft delete flag

3. **muser_package** - Assignment tracking
   - `id` - Primary key
   - `muser_id` - Foreign key to muser
   - `package_id` - Foreign key to montessori_package
   - `assigned_date` - When package was assigned
   - `click_count` - Number of times student accessed it
   - `last_accessed` - Last access timestamp

### Routes

| Route | Access | Purpose |
|-------|--------|---------|
| `/montessori/view/<token>` | Public (no login) | Student view of assigned packages |
| `/montessori/track/<token>/<package_id>` | Public (POST) | Track package clicks |
| `/montessori/admin/students` | Admin only | Manage students and tokens |
| `/montessori/admin/packages` | Admin only | Manage packages and assignments |

## Setup Instructions

### 1. Run Database Script
Replace `{schema}` with your actual schema name (e.g., `public` or `lms_prod`):

```sql
-- In your database tool, open montessori_db_setup.sql
-- Find and replace {schema} with your schema name
-- Run the script
```

Or run directly if using default schema:
```bash
psql -U your_user -d your_db -f montessori_db_setup.sql
```

### 2. Verify Python Files
The following files have been created/modified:

**New files:**
- `mm/__init__.py` - Blueprint package
- `mm/routes.py` - All route handlers
- `montessori_db_setup.sql` - Database script
- `templates/montessori_student.html` - Public student view
- `templates/montessori_admin_students.html` - Student management
- `templates/montessori_admin_packages.html` - Package management

**Modified files:**
- `models.py` - Added 3 new model classes
- `app.py` - Registered the mm blueprint

### 3. Restart Flask
```bash
# Kill current Flask process
# Restart Flask
python app.py
```

### 4. Test the System

#### Admin Student Management
1. Login as admin
2. Navigate to `/montessori/admin/students`
3. Add a new student (e.g., "John Doe")
   - System generates a unique token automatically
4. Copy the sharing link (button provided)
5. Example: `http://localhost:5000/montessori/view/ABC12DEF5GH8`

#### Admin Package Management
1. Navigate to `/montessori/admin/packages`
2. Create packages:
   - Fill in Title, Description, Link
   - Example: "Sensorial Activities" → https://example.com/activities
3. Assign packages to students in the "Assignments" tab
4. View click tracking

#### Student Access (Public)
1. Open the copied URL in a new browser (no login needed)
2. Student sees their name and assigned packages
3. Clicking a package increments the view counter
4. Admin dashboard shows click counts and last access date

## Security Notes

✅ **Tokens are unique and secure:**
- 12-character random alphanumeric strings
- Cannot access other students' packages
- Expiration happens by deleting the user (hard delete)

✅ **No login required for students:**
- Token acts as access credential
- Perfect for sharing with parents
- Can't be guessed (token verification required)

## Workflow Example

**Teacher Setup:**
1. Create student: "Alice (Parent: Sarah)" → Token: `ALICE123XYZ`
2. Create package: "Letter Writing Exercises" → Link: `/materials/letters`
3. Assign package to Alice
4. Copy link: `http://yourapp.com/montessori/view/ALICE123XYZ`
5. Email/message link to parent

**Parent Access:**
1. Receives link from teacher
2. Clicks link anytime
3. Sees Alice's name and materials
4. Each click tracked

**Admin Dashboard:**
1. Sees Alice has 8 clicks on "Letter Writing"
2. Last accessed: Today at 2:45 PM
3. Can reassign different packages anytime

## Customization Ideas

Want to add:
- **Student progress tracking?** Add a `status` field to `muser_package` (started/in-progress/completed)
- **Expiring tokens?** Add `expires_at` to `MUser` and check in verify_token
- **Comments from parents?** Create a separate feedback table
- **Package categories?** Add `category` to `montessori_package`
- **Email notifications?** Send token link automatically when assigned

## Troubleshooting

**"Invalid or expired access link"**
- ✓ Verify token matches what was copied
- ✓ Check if student was deleted (token expires)
- ✓ Check database has the muser record

**Templates not showing**
- ✓ Clear browser cache
- ✓ Check template file names match exactly
- ✓ Verify `templates/` folder contains the 3 new .html files

**Routes not working**
- ✓ Ensure `mm_bp` is registered in `app.py`
- ✓ Check `models.py` has the 3 new classes
- ✓ Restart Flask after code changes
