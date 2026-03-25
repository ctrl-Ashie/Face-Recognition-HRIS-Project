# Face Recognition HRIS

A Python desktop HRIS with face-based verification for attendance, including a dedicated employee app and a separate, database-backed admin/manager app.

## What Was Improved

1. Fixed log summary graph accuracy:

- Log summary now accurately records earliest Time-In and latest Time-Out per day.
- Missing dates for a view no longer inject fake default values, leaving gaps or falling back correctly.
- Dynamic Y-axis depending on check-in/-out times.
- Graph and stats now reflect real logs only.

2. Created completely separate admin entry point & Corporate Hierarchy:

- New standalone launcher: `admin_app.py`.
- Removed Admin tools section from Employee app completely (`main.py`).
- Admin app implements **Database-backed Authentication** allowing managers to log in autonomously with their own ID/Passwords.
- Added corporate relationships: employees can be tied to a `manager_id`.
- Added custom schedule tracking (`schedule_time_in`, `schedule_time_out`) per employee.
- Managers can ONLY see and edit profiles/logs of their direct subordinates.
- Managers cannot edit their own profiles inside the admin app.
- Implemented a "Register Manager" portal for the very first setup via a SysAdmin secret.

3. Configured cloud-capable shared storage:

- `storage.py` fully supports two backends: Local SQLite (`sqlite`) and Shared Supabase DB (`supabase`).
- In Supabase mode, admins running the portal on different systems see identical logged attendance and logs.

4. Improved face verification accuracy & robustness:

- Upgraded feature pipeline with grid-based spatial Local Binary Patterns (Spatial LBP).
- Employs downsampled central crops + aggregated regional block histograms for strict position-dependent face checks drastically reducing global false positives.
- Tightened impostor margins and recognition thresholds.

5. General cleanup:

- Added explanatory comments/docstrings in core sections.
- Updated requirements and runtime configuration docs.

## Project Structure

```text
main.py             # Employee app (signup/login, camera, verification, attendance, employee logs)
admin_app.py        # Standalone admin app (global employee and log management)
Menu.py             # Admin panel UI widgets/editors used by main/admin app
face_service.py     # Face feature extraction, template creation, verification logic
storage.py          # Dual backend storage layer (SQLite or Supabase REST)
requirements.txt    # Python dependencies
data/               # Runtime data folder (local mode)
  hris.db           # SQLite database (local mode)
  faces/            # Per-employee face samples and templates
```

## Requirements

- Python 3.9+
- Webcam accessible by OpenCV
- Optional: `BCLogo.png` in project root

Install dependencies:

```bash
pip install -r requirements.txt
```

## Running Apps

Run employee app:

```bash
python main.py
```

Run standalone admin app:

```bash
python admin_app.py
```

Default admin credentials (if env vars are not set):

- Username: `admin`
- Password: `admin123`

## Storage Backends

### 1. Local mode (default)

No extra setup needed.

```env
HRIS_STORAGE_BACKEND=sqlite
```

### 2. Shared cloud mode (Supabase)

Set environment variables (for all employee/admin devices):

```env
HRIS_STORAGE_BACKEND=supabase
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=YOUR_SUPABASE_ANON_OR_SERVICE_KEY
HRIS_ADMIN_USER=admin
HRIS_ADMIN_PASS=change_me
```

Create these tables in Supabase (SQL editor):

```sql
create table if not exists employees (
  employee_id text primary key,
  full_name text not null,
  department text not null,
  role_position text not null,
  contact_number text not null,
  email text not null,
  created_at text not null
);

create table if not exists attendance_logs (
  id bigint generated always as identity primary key,
  employee_id text not null references employees(employee_id) on delete cascade,
  action text not null,
  timestamp text not null,
  verified boolean not null,
  score double precision
);

create table if not exists verification_logs (
  id bigint generated always as identity primary key,
  employee_id text,
  success boolean not null,
  score double precision,
  message text not null,
  timestamp text not null
);

create table if not exists error_logs (
  id bigint generated always as identity primary key,
  employee_id text,
  score double precision,
  message text not null,
  timestamp text not null
);
```

## Functional Sections

### Employee app (`main.py`)

- Auth section: employee login/signup and profile validation.
- Biometric section: face enrollment and verification before attendance actions.
- Logs section: employee-specific attendance logs, error logs, and accurate summary chart.

### Admin app (`admin_app.py` + `Menu.py`)

- Completely separate entry point from the employee app.
- Auth gate for admin credentials.
- Full employee list with profile update/delete.
- Full log visibility across all employees.
- Editable attendance, verification, and error logs.

### Face services (`face_service.py`)

- Face sample management and template generation.
- Enhanced spatial block-based face embedding extraction (Spatial LBP).
- Multi-frame verification with threshold and impostor-margin checks resulting in lower false positives.

### Storage layer (`storage.py`)

- Common API for both local SQLite and Supabase cloud backend.
- Employee CRUD + attendance logs + verification/error logs.
- Daily summary aggregation and log editing support.

## Notes

- For better accuracy: use stable lighting, frontal face, and minimal motion blur.
- Re-enrollment replaces old local samples/templates for that employee.
- In cloud mode, all clients must share the same Supabase project/credentials.
