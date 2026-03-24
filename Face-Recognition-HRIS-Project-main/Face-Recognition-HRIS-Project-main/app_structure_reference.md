# App Structure Reference

This document provides a structured breakdown of the HRIS and Face Recognition Desktop App. It is designed to assist in creating Data Flow Diagrams (DFDs) and application flowcharts.

## 1. Major Modules / Sections

### A. Employee Authentication Section (auth)
- **Purpose**: Let employees either log into an existing account or register a new one.
- **Components**:
  - **Login**: Validates existing Employee ID.
  - **Signup**: Collects new employee registration details.

### B. Biometric Workspace Section (biometric)
- **Purpose**: Uses the webcam to either enroll an employee's face or verify their face before checking in/out.
- **Components**:
  - **Camera Feed**: Live video stream.
  - **Enrollment Mode**: Captures multiple face samples, then calculates facial embeddings (Spatial LBP).
  - **Verification Mode**: Scans current live frame and checks against the stored facial template.

### C. Employee Logs Section (logs)
- **Purpose**: Allows authorized, active employees to view their past check-ins/check-outs and access graphical summaries.

### D. Admin App / Panel (`admin_app.py`, `Menu.py`)
- **Purpose**: A separated executable managing global HR tracking, deleting records, fixing attendance discrepancies.
- **Components**: 
  - Admin Login Gate (DB-backed hashed authentication).
  - Register Manager (SysAdmin Secret required to promote standard employees).
  - Filtered Employees List (Locks view to the manager's assigned `manager_id`).
  - Attendance Logs List & Editor
  - Overview Summary

## 2. User Inputs & Associated Data

- **Employee ID** (Login/Signup): Text string, unique identifier.
- **Profile Fields** (Signup - Full Name, Dept, Role, Contact, Email): Text strings to track employee metadata.
- **Corporate Hierarchy Fields**: Manager ID linking, internal `is_admin` auth flag, Schedules (`time_in` / `time_out`).
- **Biometric Face Samples**: OpenCV matrices (video frames) parsed and converted into `template_vectors.npy`.
- **Attendance Action** (Biometric): `TIME IN` or `TIME OUT` triggers logged alongside a timestamp and a security verification flag.
- **Manager Credentials** (Admin App): Secure ID and raw password strings matched against a hashed `password_hash` column.
- **SysAdmin Secret**: A highly restricted backdoor (auto-generated into `.env` upon first launch of `admin_app.py`) used solely to upgrade an existing standard account to a Manager status.

## 3. Core Processes & Logic
1. **Validation & Checks**: App runs validations guaranteeing inputs are filled and valid before hitting the DB.
2. **Facial Pre-processing**: 
   - Converts frames to grayscale.
   - Applies CLAHE, Gaussian Blurs.
   - Uses Spatial Local Binary Patterns (4x4 grids + central cropping).
3. **Multi-Frame Verification**: Live face is matched against the generated template vector using peak/mean combinations, ensuring threshold > `0.88` under strict margin.
4. **Summary Aggregation**: Generates average daily statistics by mapping entries in the DB to date buckets, outputting exact earliest-in and latest-out times.

## 4. Data Flows

- **User -> Auth Form**: Data moves to `storage.py` and checked against an SQLite/Supabase backend.
- **Webcam -> UI -> face_service.py**: Raw frames traverse into `cv2` matrices, transform into numpy arrays, and persist locally under `/data/faces/EMP_ID/`.
- **face_service.py -> Verifier Engine**: Extracted Numpy templates compare actively to newly verified inputs. Result dictates success/failure logic state.
- **Storage/Database -> Log Summaries**: UI charts query `storage.py`, parse timestamps chronologically, and load the graphical rendering (`matplotlib`).

## 5. Outputs
- UI Navigation (Access allowed / Access denied).
- Green/Red success status overlays and inline popups.
- Interactive Matplotlib visual graphs.

## 6. External Dependencies
- OpenCV (`cv2`) for webcam operation.
- SQLite3 or Supabase (REST `requests`) for storage.
- Numpy for mathematical and array computation.
- Tkinter for native interface.
- Matplotlib for charts.