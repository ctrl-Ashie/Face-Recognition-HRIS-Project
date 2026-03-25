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

---

## 7. Flowchart Mapping (For Diagramming)

Use the following step-by-step logic paths to easily draw application Flowcharts.

### A. Employee App Flow (`main.py`)
1. **Start** -> Launch `main.py`.
2. **Decision**: Does the user have an account?
   - *No*: Fill Signup Form -> Validate fields -> Save to DB (`manager_id` defaults to NULL) -> Proceed to Biometrics.
   - *Yes*: Enter ID -> Query DB -> **Decision**: Exists? -> Proceed to Biometrics.
3. **Decision View Mode**:
   - *Select Enroll*: Capture 10 frames -> Compute LBP -> Save `template_vectors.npy`.
   - *Select Time In/Out*: Load `template_vectors.npy` -> Capture live frames -> Compare -> **Decision**: Match > 0.88?
     - *Yes*: Insert `TIME_IN` or `TIME_OUT` to DB -> Show Success.
     - *No*: Log Failure to `error_logs` in DB -> Show Denied.
   - *Select Logs*: Query DB for User's ID -> Generate Matplotlib Chart.

### B. Admin / Manager App Flow (`admin_app.py`)
1. **Start** -> Launch `admin_app.py`.
2. **System Check**: Does `.env` have `HRIS_SYSADMIN_SECRET`?
   - *No*: Auto-generate key -> Save to `.env` -> Show Setup Popup with Key -> Wait for user to click "Continue".
   - *Yes*: Load normally.
3. **Decision at Login Gateway**:
   - *Path 1: Login*: Enter Manager ID & Password -> Fetch from DB -> **Condition**: `is_admin == 1` AND Passwords match? -> Open Admin Panel.
   - *Path 2: Register Manager*: Enter SysAdmin Secret, Target ID, New Password -> Validate Secret -> Hash Password -> Update DB `is_admin=1` -> Return to Login.
4. **Inside Admin Panel (Manager View)**:
   - *Fetch Data*: Query `employees` WHERE `manager_id = logged_in_user` OR `manager_id IS NULL`. 
   - *Action: Assign Team*: Manager selects a NULL employee -> Sets Manager ID -> Updates DB -> Employee is permanently locked to this Manager's team.
   - *Action: View Logs*: App gathers all subordinate IDs -> Queries `attendance_logs` matching only those IDs -> Displays Filtered Charts.

---

## 8. Data Flow Diagram (DFD) Entity Mapping

Use these variables to create Level 0 and Level 1 DFDs.

### External Entities (Squares)
- **Employee**: Interacts with the Main App to clock in/out or view their personal stats.
- **Manager**: Interacts with the Admin App to assign teams, fix attendance, and view departmental reports.
- **SysAdmin**: The overarching role that handles the `.env` secret key to promote initial managers.

### Core Processes (Circles / Rounded Rectangles)
- **P1 - Employee Management**: Saving new employee profiles and updating `manager_id` or schedules.
- **P2 - Biometric Engine**: Converting live faces to matrices and comparing against saved `.npy` templates.
- **P3 - Attendance Tracker**: Writing clock-in/out timestamps upon successful P2 validation.
- **P4 - Authentication & Promotion**: Validating SysAdmin secrets, hashing admin passwords, and verifying manager logins.
- **P5 - Reporting & Analytics**: Performing relational joins (`INNER JOIN`) to filter logs strictly to a manager's authorized team IDs.

### Data Stores (Open-ended Rectangles)
- **D1 - Employees Table**: Stores IDs, profiles, `manager_id`, schedules, `is_admin` flags, and password hashes.
- **D2 - Attendance & Error Logs**: Stores chronological transactions with success/failure flags.
- **D3 - Biometric Vault**: Local directory (`/data/faces/`) storing isolated Numpy templates.
- **D4 - Environment File**: Local `.env` containing connection strings (Supabase) and the SysAdmin Secret.