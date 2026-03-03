# Face-Recognition-HRIS

A desktop HRIS (Human Resource Information System) application with face-recognition-based employee verification, built with Python, Tkinter, and OpenCV.

## Current Features

- Non-overlapping grid-based UI layout (header, camera pane, profile/actions pane, status bar).
- Live webcam feed with face detection overlay and quality filtering.
- Employee signup with required profile fields:
  - Employee ID
  - Full Name
  - Department
  - Role/Position
  - Contact Number
  - Email
- Face enrollment during signup (10 valid samples captured from webcam).
- Face re-enrollment for existing employees through Admin panel.
- Employee verification using Employee ID + local multi-frame template matching.
- Security checks: quality filtering + claimed-ID threshold + impostor-margin comparison.
- In-app verification state shown as `VERIFIED` or `UNVERIFIED`.
- Attendance logging with separate `Time In` and `Time Out` actions.
- Attendance rules:
  - Prevents repeated consecutive `Time In`.
  - Prevents `Time Out` before a valid `Time In`.
- Header actions display:
  - User Logs (attendance records)
  - Log Error (failed verification attempts)
  - Log Summary (daily totals)
  - Admin Panel

## Admin Panel (Testing Scope)

- View all employee accounts and full profile details.
- View saved face photos per employee with photo preview.
- Update employee profile fields (including Employee ID).
- Trigger re-enrollment of face samples.
- Hard delete employee data (employee record + attendance logs + verification logs + saved photos).
- View verification and attendance logs.

## Data Storage

- SQLite database: `data/hris.db`
- Face samples: `data/faces/<employee_id>/sample_XX.png`
- Face templates: `data/faces/<employee_id>/template_vectors.npy`

The application creates these paths automatically on first run.

## Project Structure

```
main.py             # Entry point – Tkinter GUI, camera loop, signup & verification logic
Menu.py             # Admin Panel (employee CRUD, photo viewer, log inspection)
face_service.py     # Face detection, preprocessing, template building & verification
storage.py          # SQLite database helpers (employees, attendance, verification logs)
requirements.txt    # Python package dependencies
data/               # Auto-created at runtime
  hris.db           # SQLite database
  faces/            # Per-employee face samples and templates
```

## Requirements

- Python 3.9+
- A webcam accessible by OpenCV
- (Optional) `BCLogo.png` in the project root for the header logo

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:

   ```bash
   python main.py
   ```

## How to Use

1. Signup an employee:
	- Fill all profile fields.
	- Click `Start Signup`.
	- Keep one face in frame until `10/10` valid samples are captured.

2. Verify identity:
	- Enter employee ID.
	- Click `Verify Identity`.
	- Hold steady briefly so enough recent frames are collected.
	- When successful, the app shows `VERIFIED` and employee details.

3. Log attendance:
	- Click `Time In` or `Time Out` after successful verification.

4. Admin operations:
	- Click `Admin Panel` in the header.
	- Manage employees, photos, updates, re-enrollment, deletions, and log inspection.

## Notes

- Re-enrollment immediately invalidates old templates and rebuilds from new samples.
- For best matching results, use good lighting, keep one face centered, and avoid motion blur during verification.