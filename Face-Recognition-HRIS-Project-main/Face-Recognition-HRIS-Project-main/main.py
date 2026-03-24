import re
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import cv2
import numpy as np
from dotenv import load_dotenv
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from face_service import (
    MAX_SAMPLES,
    REQUIRED_VERIFY_FRAMES,
    build_employee_template,
    clear_employee_samples,
    get_face_region,
    load_employee_template,
    save_face_sample,
    verify_claimed_employee,
)
from storage import (
    add_employee,
    can_log_action,
    employee_exists,
    get_employee,
    get_employee_attendance,
    get_recent_verification_errors,
    init_db,
    list_employees,
    log_attendance,
    log_verification,
)

BG_COLOR = "light gray"
HEADER_COLOR = "#010066"
ACCENT_COLOR = "#caab2f"
FORM_BG = "#e1e1e1"
LOGO_PATH = "BCLogo.png"

EMPLOYEE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,19}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class HRISApp:
    """Primary employee-facing app (auth, camera verification, attendance, and employee-scoped logs)."""

    def __init__(self):
        # Load optional .env settings for storage backend and admin credentials.
        load_dotenv()
        init_db()

        self.window = tk.Tk()
        self.window.title("Face Recognition HRIS")
        self.window.minsize(1120, 700)
        self.window.config(bg=BG_COLOR)

        self.logo_img = None
        self.status_text = tk.StringVar(value="Welcome. Start from Employee Login / Signup.")

        self.logged_in_employee_id = None
        self.pending_attendance_action = None

        self.mode = "idle"
        self.enroll_profile = {}
        self.enroll_count = 0
        self.capture_cooldown = 0
        self.reenroll_existing = False
        self.verify_frames = []

        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.cap = cv2.VideoCapture(0)

        self._build_ui()
        self._setup_camera()
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        # Global shell: header, navigation, section container, and status bar.
        header = tk.Frame(self.window, bg=HEADER_COLOR, padx=10, pady=8)
        header.pack(side="top", fill="x")

        logo = self._get_logo()
        if logo is not None:
            tk.Label(header, image=logo, bg=HEADER_COLOR).pack(side="left")

        tk.Label(
            header,
            text="Face Recognition HRIS",
            bg=HEADER_COLOR,
            fg="white",
            font=("Times New Roman", 20, "bold"),
        ).pack(side="left", padx=10)

        self.session_label = tk.Label(
            header,
            text="Employee Session: Not Logged In",
            bg=HEADER_COLOR,
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.session_label.pack(side="right")

        nav = tk.Frame(self.window, bg=BG_COLOR)
        nav.pack(fill="x", padx=10, pady=(8, 0))

        self.section_buttons = {
            "auth": tk.Button(nav, text="Employee Login / Signup", command=lambda: self._show_section("auth"), bg=ACCENT_COLOR),
            "biometric": tk.Button(nav, text="Biometric Workspace", command=lambda: self._show_section("biometric"), state="disabled"),
            "logs": tk.Button(nav, text="Employee Logs", command=lambda: self._show_section("logs"), state="disabled"),
        }

        self.section_buttons["auth"].pack(side="left", padx=(0, 6), pady=4)
        self.section_buttons["biometric"].pack(side="left", padx=6, pady=4)
        self.section_buttons["logs"].pack(side="left", padx=6, pady=4)

        self.logout_btn = tk.Button(nav, text="Logout Employee", command=self._logout_employee, state="disabled")
        self.logout_btn.pack(side="right", padx=4)

        self.section_container = tk.Frame(self.window, bg=BG_COLOR)
        self.section_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.section_frames = {
            "auth": tk.Frame(self.section_container, bg=BG_COLOR),
            "biometric": tk.Frame(self.section_container, bg=BG_COLOR),
            "logs": tk.Frame(self.section_container, bg=BG_COLOR),
        }

        self._build_auth_section(self.section_frames["auth"])
        self._build_biometric_section(self.section_frames["biometric"])
        self._build_logs_section(self.section_frames["logs"])

        self._show_section("auth")

        status_bar = tk.Label(
            self.window,
            textvariable=self.status_text,
            anchor="w",
            bg=HEADER_COLOR,
            fg="white",
            padx=10,
            pady=6,
        )
        status_bar.pack(side="bottom", fill="x")

    def _build_auth_section(self, parent):
        # Account access section: employee login and employee signup.
        panel = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1, padx=14, pady=14)
        panel.pack(fill="both", expand=True)

        tk.Label(panel, text="Employee Account Access", bg=FORM_BG, fg=HEADER_COLOR, font=("Arial", 16, "bold")).pack(anchor="w")
        tk.Label(
            panel,
            text="Step 1: Login or create account. Step 2: Proceed to biometric enrollment/verification.",
            bg=FORM_BG,
            fg="#333333",
        ).pack(anchor="w", pady=(4, 12))

        login_box = tk.LabelFrame(panel, text="Login", bg=FORM_BG, padx=10, pady=10)
        login_box.pack(fill="x", pady=(0, 12))

        login_row = tk.Frame(login_box, bg=FORM_BG)
        login_row.pack(fill="x")
        tk.Label(login_row, text="Employee ID", bg=FORM_BG, width=14, anchor="w").pack(side="left")
        self.login_id_var = tk.StringVar()
        tk.Entry(login_row, textvariable=self.login_id_var).pack(side="left", fill="x", expand=True)
        tk.Button(login_row, text="Login", bg=ACCENT_COLOR, command=self._login_employee).pack(side="left", padx=(8, 0))

        signup_box = tk.LabelFrame(panel, text="Signup", bg=FORM_BG, padx=10, pady=10)
        signup_box.pack(fill="x")

        self.signup_vars = {
            "employee_id": tk.StringVar(),
            "full_name": tk.StringVar(),
            "department": tk.StringVar(),
            "role_position": tk.StringVar(),
            "contact_number": tk.StringVar(),
            "email": tk.StringVar(),
        }

        self._build_form_field(signup_box, "Employee ID", self.signup_vars["employee_id"])
        self._build_form_field(signup_box, "Full Name", self.signup_vars["full_name"])
        self._build_form_field(signup_box, "Department", self.signup_vars["department"])
        self._build_form_field(signup_box, "Role / Position", self.signup_vars["role_position"])
        self._build_form_field(signup_box, "Contact Number", self.signup_vars["contact_number"])
        self._build_form_field(signup_box, "Email", self.signup_vars["email"])

        tk.Button(signup_box, text="Create Account", bg=ACCENT_COLOR, command=self._signup_employee).pack(fill="x", pady=(8, 0))

    def _build_biometric_section(self, parent):
        # Camera workspace for enrollment and attendance verification workflows.
        left = tk.Frame(parent, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1)
        right.pack(side="right", fill="y", padx=(10, 0))

        self.cam_label = tk.Label(left, bg="black")
        self.cam_label.pack(fill="both", expand=True)

        self.profile_label = tk.Label(
            left,
            text="No employee session",
            font=("Arial", 11, "bold"),
            bg=FORM_BG,
            fg="black",
            justify="left",
            anchor="nw",
            padx=8,
            pady=8,
            height=7,
        )
        self.profile_label.pack(fill="x", pady=(8, 0))

        tk.Label(right, text="Biometric Enrollment", bg=FORM_BG, font=("Arial", 12, "bold")).pack(anchor="w", padx=10, pady=(8, 4))
        tk.Label(
            right,
            text="Use this for initial enrollment or re-enrollment.",
            bg=FORM_BG,
            fg="#333333",
            wraplength=260,
            justify="left",
        ).pack(anchor="w", padx=10)
        tk.Button(right, text="Start Face Enrollment", bg=ACCENT_COLOR, command=self.start_enrollment).pack(fill="x", padx=10, pady=(8, 10))

        tk.Label(right, text="Attendance (Verification Required Each Action)", bg=FORM_BG, font=("Arial", 12, "bold")).pack(
            anchor="w", padx=10, pady=(8, 4)
        )
        tk.Button(
            right,
            text="Verify and Time In",
            bg=ACCENT_COLOR,
            command=lambda: self.start_verification_for_action("TIME_IN"),
        ).pack(fill="x", padx=10, pady=(4, 6))
        tk.Button(
            right,
            text="Verify and Time Out",
            bg=ACCENT_COLOR,
            command=lambda: self.start_verification_for_action("TIME_OUT"),
        ).pack(fill="x", padx=10, pady=(0, 10))

        self.mode_label = tk.Label(right, text="Mode: Idle", bg=FORM_BG, fg=HEADER_COLOR, font=("Arial", 10, "bold"))
        self.mode_label.pack(fill="x", padx=10, pady=(0, 6))

        self.capture_label = tk.Label(right, text=f"Captured: 0/{MAX_SAMPLES}", bg=FORM_BG, fg="black")
        self.capture_label.pack(fill="x", padx=10, pady=(0, 8))

    def _build_logs_section(self, parent):
        # Employee-only log views and summary analytics.
        panel = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1, padx=14, pady=14)
        panel.pack(fill="both", expand=True)

        tk.Label(panel, text="Employee Logs", bg=FORM_BG, fg=HEADER_COLOR, font=("Arial", 16, "bold")).pack(anchor="w")
        self.logs_scope_label = tk.Label(
            panel,
            text="Available only when employee is logged in.",
            bg=FORM_BG,
            fg="#333333",
        )
        self.logs_scope_label.pack(anchor="w", pady=(4, 12))

        action_row = tk.Frame(panel, bg=FORM_BG)
        action_row.pack(fill="x", pady=(6, 8))
        tk.Button(action_row, text="User Logs", bg=ACCENT_COLOR, command=self.user_logs_clicked).pack(side="left", padx=(0, 8))
        tk.Button(action_row, text="Log Error", bg=ACCENT_COLOR, command=self.log_error_clicked).pack(side="left", padx=8)
        tk.Button(action_row, text="Log Summary", bg=ACCENT_COLOR, command=self.log_summary_clicked).pack(side="left", padx=8)

    def _build_form_field(self, parent, label, var):
        # Wraps labels alongside text string entry variables enforcing padding constraints.
        row = tk.Frame(parent, bg=FORM_BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=FORM_BG, width=15, anchor="w").pack(side="left")
        tk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True)

    def _show_section(self, section):
        """Displays designated UI segments selectively masking hidden panels simulating app navigation."""
        if section in {"biometric", "logs"} and not self.logged_in_employee_id:
            messagebox.showwarning("Employee Session", "Login first to access this section.")
            section = "auth"

        for key, frame in self.section_frames.items():
            if key == section:
                frame.pack(fill="both", expand=True)
                self.section_buttons[key].config(bg=ACCENT_COLOR)
            else:
                frame.pack_forget()
                self.section_buttons[key].config(bg="white")

    def _set_mode(self, mode):
        self.mode = mode
        self.mode_label.config(text=f"Mode: {mode.replace('_', ' ').title()}")

    def _set_status(self, message):
        self.status_text.set(message)

    def _get_logo(self):
        if self.logo_img is not None:
            return self.logo_img

        try:
            image = Image.open(LOGO_PATH)
            image = image.resize((44, 44), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(image)
            return self.logo_img
        except Exception:
            return None

    def _setup_camera(self):
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.cam_w = 700
            self.cam_h = int(self.cam_w * h / w)
        else:
            self.cam_w = 700
            self.cam_h = 525
        self.cam_label.config(width=self.cam_w, height=self.cam_h)
        self.update_camera()

    def _validate_profile(self):
        """Cross-checks required profile information against strict patterns and displays inline warning criteria."""
        profile = {key: var.get().strip() for key, var in self.signup_vars.items()}

        missing = [key for key, value in profile.items() if not value]
        if missing:
            return None, "ERROR: All signup fields are required to prevent data loss."

        if not EMPLOYEE_ID_PATTERN.match(profile["employee_id"]):
            return None, "ERROR: Employee ID strictly must be 3-20 chars using letters, numbers, _ or -."

        if not EMAIL_PATTERN.match(profile["email"]):
            return None, "ERROR: Email format is logically inconsistent or invalid."

        digits = re.sub(r"\D", "", profile["contact_number"])
        if len(digits) < 7 or len(digits) > 15:
            return None, "ERROR: Contact number must contain between 7 to 15 digits."

        if employee_exists(profile["employee_id"]):
            return None, "CONFLICT: Employee ID already exists in the backend database."

        return profile, "OK"

    def _validate_face_quality(self, face_crop):
        if face_crop is None or face_crop.size == 0:
            return False, "No face detected."

        h, w = face_crop.shape[:2]
        if h < 80 or w < 80:
            return False, "Face too small. Move closer to camera."

        gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        brightness = float(np.mean(gray))
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())

        if brightness < 50:
            return False, "Image too dark. Improve lighting."
        if blur < 80:
            return False, "Image too blurry. Hold still."

        return True, "OK"

    def _login_employee(self):
        employee_id = self.login_id_var.get().strip()
        if not employee_id:
            messagebox.showerror("Login", "Enter Employee ID.")
            return

        employee = get_employee(employee_id)
        if employee is None:
            messagebox.showerror("Login", "Employee account not found.")
            return

        self._activate_employee_session(employee_id)
        self._show_section("biometric")

        if load_employee_template(employee_id) is None:
            self._set_status("Login successful. No biometric template found; start enrollment next.")
        else:
            self._set_status("Login successful. Proceed to verification for each attendance action.")

    def _signup_employee(self):
        profile, msg = self._validate_profile()
        if profile is None:
            messagebox.showerror("Signup", msg)
            return

        try:
            add_employee(
                profile["employee_id"],
                profile["full_name"],
                profile["department"],
                profile["role_position"],
                profile["contact_number"],
                profile["email"],
            )
        except Exception as exc:
            messagebox.showerror("Signup", f"Unable to create account: {exc}")
            return

        for var in self.signup_vars.values():
            var.set("")

        self._activate_employee_session(profile["employee_id"])
        self._show_section("biometric")
        self._set_status("Account created. Continue with biometric enrollment.")

    def _activate_employee_session(self, employee_id):
        self.logged_in_employee_id = employee_id
        self.session_label.config(text=f"Employee Session: {employee_id}")
        self.logout_btn.config(state="normal")
        self.section_buttons["biometric"].config(state="normal")
        self.section_buttons["logs"].config(state="normal")
        self.logs_scope_label.config(text=f"Viewing logs for logged in employee: {employee_id}")

        employee = get_employee(employee_id)
        if employee:
            self.profile_label.config(
                text=(
                    f"SESSION ACTIVE\n"
                    f"ID: {employee['employee_id']}\n"
                    f"Name: {employee['full_name']}\n"
                    f"Dept: {employee['department']}\n"
                    f"Role: {employee['role_position']}"
                )
            )

    def _logout_employee(self):
        self.logged_in_employee_id = None
        self.pending_attendance_action = None
        self.verify_frames = []
        self.enroll_profile = {}
        self.enroll_count = 0
        self.reenroll_existing = False
        self._set_mode("idle")
        self.capture_label.config(text=f"Captured: 0/{MAX_SAMPLES}")

        self.session_label.config(text="Employee Session: Not Logged In")
        self.logout_btn.config(state="disabled")
        self.section_buttons["biometric"].config(state="disabled")
        self.section_buttons["logs"].config(state="disabled")
        self.logs_scope_label.config(text="Available only when employee is logged in.")
        self.profile_label.config(text="No employee session")

        self._show_section("auth")
        self._set_status("Employee logged out.")

    def _require_employee_session(self):
        if not self.logged_in_employee_id:
            messagebox.showwarning("Employee Session", "Login first.")
            self._show_section("auth")
            return False
        return True

    def start_enrollment(self):
        if not self._require_employee_session():
            return

        if self.mode != "idle":
            messagebox.showwarning("Enrollment", "System is busy. Finish current action first.")
            return

        employee = get_employee(self.logged_in_employee_id)
        if employee is None:
            messagebox.showerror("Enrollment", "Employee profile not found.")
            return

        self.enroll_profile = employee
        self.enroll_count = 0
        self.capture_cooldown = 0
        self.reenroll_existing = True

        clear_employee_samples(self.logged_in_employee_id)
        self.capture_label.config(text=f"Captured: 0/{MAX_SAMPLES}")
        self._set_mode("signup")
        self._set_status("Enrollment started. Keep one face centered until all samples are captured.")

    def start_verification_for_action(self, action):
        if not self._require_employee_session():
            return

        if self.mode != "idle":
            messagebox.showwarning("Verification", "System is busy. Finish current action first.")
            return

        if load_employee_template(self.logged_in_employee_id) is None:
            messagebox.showwarning("Verification", "No enrolled template found. Run enrollment first.")
            self._set_status("Verification denied: No enrolled template found.")
            log_verification(self.logged_in_employee_id, False, None, "No enrolled template found for employee.")
            return

        self.pending_attendance_action = action
        self.verify_frames = []
        self.capture_cooldown = 0
        self._set_mode("verify")
        self._set_status(
            f"Verification started for {action.replace('_', ' ')}. Hold still for {REQUIRED_VERIFY_FRAMES} frames."
        )

    def _handle_signup_frame(self, frame, face_rect):
        if self.capture_cooldown > 0:
            self.capture_cooldown -= 1
            return

        face_crop = get_face_region(frame, face_rect)
        is_valid, reason = self._validate_face_quality(face_crop)
        if not is_valid:
            self._set_status(f"Invalid biometric sample: {reason}")
            self.capture_cooldown = 10
            return

        self.enroll_count += 1
        employee_id = self.enroll_profile["employee_id"]
        save_face_sample(employee_id, face_crop, self.enroll_count)
        self.capture_label.config(text=f"Captured: {self.enroll_count}/{MAX_SAMPLES}")
        self._set_status(f"Sample {self.enroll_count}/{MAX_SAMPLES} saved.")
        self.capture_cooldown = 8

        if self.enroll_count >= MAX_SAMPLES:
            try:
                build_employee_template(employee_id)
            except Exception as exc:
                self._set_status(f"Enrollment failed: {exc}")
                messagebox.showerror("Enrollment", f"Failed to complete enrollment: {exc}")
                clear_employee_samples(employee_id)
            else:
                messagebox.showinfo("Enrollment", f"Enrollment complete for {employee_id}.")
                self._set_status(f"Enrollment complete for {employee_id}.")
            finally:
                self.enroll_profile = {}
                self.enroll_count = 0
                self.reenroll_existing = False
                self.capture_label.config(text=f"Captured: 0/{MAX_SAMPLES}")
                self._set_mode("idle")

    def _handle_verify_frame(self, frame, face_rect):
        face_crop = get_face_region(frame, face_rect)
        valid, reason = self._validate_face_quality(face_crop)
        if not valid:
            self._set_status(f"Verification frame rejected: {reason}")
            return

        self.verify_frames.append(face_crop)
        if len(self.verify_frames) > REQUIRED_VERIFY_FRAMES:
            self.verify_frames.pop(0)

        self._set_status(
            f"Collecting frames for verification: {len(self.verify_frames)}/{REQUIRED_VERIFY_FRAMES}"
        )

        if len(self.verify_frames) < REQUIRED_VERIFY_FRAMES:
            return

        all_ids = [row["employee_id"] for row in list_employees()]
        result = verify_claimed_employee(self.logged_in_employee_id, self.verify_frames, all_ids)

        log_verification(
            self.logged_in_employee_id,
            bool(result["matched"]),
            float(result["score"]),
            str(result["reason"]),
        )

        if result["matched"]:
            action = self.pending_attendance_action
            can_log, msg = can_log_action(self.logged_in_employee_id, action)
            if not can_log:
                messagebox.showwarning("Attendance", msg)
                self._set_status(msg)
            else:
                log_attendance(self.logged_in_employee_id, action, True, float(result["score"]))
                messagebox.showinfo("Attendance", f"{action.replace('_', ' ')} recorded.")
                self._set_status(f"{action.replace('_', ' ')} recorded after successful verification.")

            self.profile_label.config(
                text=(
                    f"VERIFIED FOR ACTION\n"
                    f"ID: {self.logged_in_employee_id}\n"
                    f"Action: {action.replace('_', ' ')}\n"
                    f"Score: {float(result['score']):.3f}"
                )
            )
        else:
            self._set_status(f"Verification failed: {result['reason']}")
            messagebox.showerror("Verification", result["reason"])

        self.pending_attendance_action = None
        self.verify_frames = []
        self._set_mode("idle")

    def update_camera(self):
        ret, frame = self.cap.read()
        if not ret:
            self.window.after(30, self.update_camera)
            return

        frame = cv2.resize(frame, (self.cam_w, self.cam_h))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

        chosen_face = None
        if len(faces) > 0:
            chosen_face = max(faces, key=lambda rect: rect[2] * rect[3])

        for (x, y, w, h) in faces:
            color = (0, 255, 0) if chosen_face is not None and (x, y, w, h) == tuple(chosen_face) else (255, 255, 0)
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

        if self.mode == "signup" and chosen_face is not None:
            self._handle_signup_frame(frame, tuple(chosen_face))
        elif self.mode == "verify" and chosen_face is not None:
            self._handle_verify_frame(frame, tuple(chosen_face))
        elif self.mode in {"signup", "verify"} and chosen_face is None:
            self._set_status("No face detected. Please face the camera.")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        image_tk = ImageTk.PhotoImage(image=image)
        self.cam_label.imgtk = image_tk
        self.cam_label.configure(image=image_tk)

        self.window.after(30, self.update_camera)

    def _resolve_target_employee_id(self):
        return self.logged_in_employee_id

    def user_logs_clicked(self):
        target_employee_id = self._resolve_target_employee_id()
        if not target_employee_id:
            messagebox.showwarning("User Logs", "Login first.")
            return

        logs = get_employee_attendance(target_employee_id, limit=300)
        sorted_logs = sorted(logs, key=lambda row: row["timestamp"])

        session_rows = []
        day_sessions = {}
        for row in sorted_logs:
            stamp = datetime.fromisoformat(row["timestamp"])
            day_key = stamp.date().isoformat()
            day_sessions.setdefault(day_key, {"day": stamp.strftime("%A"), "time_in": "-", "time_out": "-"})

            if row["action"] == "TIME_IN":
                if day_sessions[day_key]["time_in"] != "-":
                    session_rows.append(day_sessions[day_key])
                    day_sessions[day_key] = {"day": stamp.strftime("%A"), "time_in": "-", "time_out": "-"}
                day_sessions[day_key]["time_in"] = stamp.strftime("%I:%M %p")
            elif row["action"] == "TIME_OUT":
                day_sessions[day_key]["time_out"] = stamp.strftime("%I:%M %p")
                session_rows.append(day_sessions[day_key])
                day_sessions[day_key] = {"day": stamp.strftime("%A"), "time_in": "-", "time_out": "-"}

        for session in day_sessions.values():
            if session["time_in"] != "-" or session["time_out"] != "-":
                session_rows.append(session)

        ulwindow = tk.Toplevel(self.window)
        ulwindow.title(f"User Logs - {target_employee_id}")
        ulwindow.minsize(700, 500)
        ulwindow.config(bg=BG_COLOR)

        table_frame = tk.Frame(ulwindow, bg=BG_COLOR)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        headers = ["No. of Logs", "Day", "Time In", "Time Out"]
        for col, header_text in enumerate(headers):
            tk.Label(
                table_frame,
                text=header_text,
                font=("Arial", 10, "bold"),
                bg=HEADER_COLOR,
                fg="white",
                padx=10,
                pady=10,
                relief="ridge",
                borderwidth=2,
            ).grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
            table_frame.columnconfigure(col, weight=1)

        if not session_rows:
            tk.Label(table_frame, text="No logs found.", bg="white").grid(column=0, row=1, columnspan=4, sticky="nsew")
            return

        for idx, session in enumerate(session_rows, start=1):
            row_data = [str(idx), session["day"], session["time_in"], session["time_out"]]
            for col_idx, cell_data in enumerate(row_data):
                tk.Label(
                    table_frame,
                    text=cell_data,
                    font=("Arial", 10),
                    bg="white",
                    fg="black",
                    padx=10,
                    pady=10,
                    relief="solid",
                    borderwidth=1,
                ).grid(column=col_idx, row=idx, sticky="nsew", padx=2, pady=2)

    def _classify_error(self, reason):
        text = reason.lower()
        if "at least" in text and "frame" in text:
            return "Insufficient Frames"
        if "no enrolled template" in text or "no enrolled" in text:
            return "Missing Template"
        if "consensus" in text or "threshold" in text:
            return "Threshold Consensus Fail"
        if "margin" in text or "impostor" in text:
            return "Impostor Margin Violation"
        return "Verification Failed"

    def log_error_clicked(self):
        target_employee_id = self._resolve_target_employee_id()
        if not target_employee_id:
            messagebox.showwarning("Log Error", "Login first.")
            return

        errors = [
            row
            for row in get_recent_verification_errors(limit=500)
            if (row["employee_id"] or "") == target_employee_id
        ]
        errors.sort(key=lambda row: row["timestamp"])

        lewindow = tk.Toplevel(self.window)
        lewindow.title(f"Log Error - {target_employee_id}")
        lewindow.minsize(760, 500)
        lewindow.config(bg=BG_COLOR)

        table_frame = tk.Frame(lewindow, bg=BG_COLOR)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        headers = ["No. of Error", "Day", "Time", "Type"]
        for col, header_text in enumerate(headers):
            tk.Label(
                table_frame,
                text=header_text,
                font=("Arial", 10, "bold"),
                bg=HEADER_COLOR,
                fg="white",
                padx=10,
                pady=10,
                relief="ridge",
                borderwidth=2,
            ).grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
            table_frame.columnconfigure(col, weight=1)

        if not errors:
            tk.Label(table_frame, text="No error logs found.", bg="white").grid(column=0, row=1, columnspan=4, sticky="nsew")
            return

        for idx, row in enumerate(errors, start=1):
            stamp = datetime.fromisoformat(row["timestamp"])
            row_data = [
                str(idx),
                stamp.strftime("%A"),
                stamp.strftime("%I:%M %p"),
                self._classify_error(row["message"]),
            ]
            for col_idx, cell_data in enumerate(row_data):
                tk.Label(
                    table_frame,
                    text=cell_data,
                    font=("Arial", 10),
                    bg="white",
                    fg="black",
                    padx=10,
                    pady=10,
                    relief="solid",
                    borderwidth=1,
                ).grid(column=col_idx, row=idx, sticky="nsew", padx=2, pady=2)

    def log_summary_clicked(self):
        target_employee_id = self._resolve_target_employee_id()
        if not target_employee_id:
            messagebox.showwarning("Log Summary", "Login first.")
            return

        rows = get_employee_attendance(target_employee_id, limit=500)
        if not rows:
            messagebox.showinfo("Log Summary", "No attendance logs found for employee.")
            return

        rows = sorted(rows, key=lambda row: row["timestamp"])

        # Keep real, date-based aggregates so the chart reflects actual logs, not weekday buckets.
        log_data = {}
        for row in rows:
            stamp = datetime.fromisoformat(row["timestamp"])
            day_key = stamp.date().isoformat()
            as_float = stamp.hour + (stamp.minute / 60.0)
            log_data.setdefault(day_key, {"time_in": [], "time_out": []})
            if row["action"] == "TIME_IN":
                log_data[day_key]["time_in"].append(as_float)
            elif row["action"] == "TIME_OUT":
                log_data[day_key]["time_out"].append(as_float)

        lswindow = tk.Toplevel(self.window)
        lswindow.title(f"Log Summary - {target_employee_id}")
        lswindow.minsize(820, 600)
        lswindow.config(bg=BG_COLOR)

        view_state = {"current": "time_in"}

        button_frame = tk.Frame(lswindow, bg=BG_COLOR)
        button_frame.pack(side="top", fill="x", padx=10, pady=10)

        content_frame = tk.Frame(lswindow, bg=BG_COLOR)
        content_frame.pack(fill="both", expand=True, padx=8, pady=8)

        graph_frame = tk.Frame(content_frame, bg="white", relief="solid", borderwidth=1)
        graph_frame.pack(side="left", fill="both", expand=True)

        stats_frame = tk.Frame(content_frame, bg=FORM_BG, width=220)
        stats_frame.pack(side="right", fill="both", padx=(8, 0))
        stats_frame.pack_propagate(False)

        stats_content_frame = tk.Frame(stats_frame, bg=FORM_BG)
        stats_content_frame.pack(fill="both", expand=True, padx=8, pady=8)

        time_in_btn = tk.Button(
            button_frame,
            text="Time In",
            bg=ACCENT_COLOR,
            fg="black",
            command=lambda: update_view("time_in"),
        )
        time_out_btn = tk.Button(
            button_frame,
            text="Time Out",
            bg=HEADER_COLOR,
            fg="white",
            command=lambda: update_view("time_out"),
        )
        time_in_btn.pack(side="left", padx=5)
        time_out_btn.pack(side="left", padx=5)

        def update_view(view_type):
            view_state["current"] = view_type
            if view_type == "time_in":
                time_in_btn.config(bg=ACCENT_COLOR, fg="black")
                time_out_btn.config(bg=HEADER_COLOR, fg="white")
            else:
                time_in_btn.config(bg=HEADER_COLOR, fg="white")
                time_out_btn.config(bg=ACCENT_COLOR, fg="black")
            update_graph_and_stats()

        def update_graph_and_stats():
            for widget in graph_frame.winfo_children():
                widget.destroy()
            for widget in stats_content_frame.winfo_children():
                widget.destroy()

            days = list(sorted(log_data.keys()))
            day_numbers = np.arange(len(days))
            fig = Figure(figsize=(6, 4), dpi=100)
            ax = fig.add_subplot(111)

            if view_state["current"] == "time_in":
                early_count = 0
                late_count = 0
                times_to_plot = []
                for day in days:
                    values = log_data[day]["time_in"]
                    if values:
                        earliest = min(values)  # earliest time in
                        times_to_plot.append(float(earliest))
                        if earliest <= 9.0:  # standard 9AM threshold
                            early_count += 1
                        else:
                            late_count += 1
                    else:
                        times_to_plot.append(np.nan)

                tk.Label(stats_content_frame, text=f"Early/On-time: {early_count}", bg="#106919", fg="white").pack(fill="x", pady=4)
                tk.Label(stats_content_frame, text=f"Late: {late_count}", bg="#8b221e", fg="white").pack(fill="x", pady=4)

                total = early_count + late_count
                status = "NO DATA" if total == 0 else ("LATE" if late_count > early_count else "ON TIME")
                status_bg = "#9a2925" if status == "LATE" else "#5cb85c"
                if status == "NO DATA":
                    status_bg = "#555555"
                tk.Label(stats_content_frame, text=status, bg=status_bg, fg="white", font=("Arial", 11, "bold")).pack(fill="x", pady=10)

                lines = ax.plot(day_numbers, times_to_plot, marker="o", markersize=8, linewidth=3, color="#1f77b4", label="Time In")
                ax.set_title("Earliest Time In by Day", fontsize=14, fontweight="bold", pad=10)
                
                # Dynamic Y-axis
                if any(not np.isnan(v) for v in times_to_plot):
                    valid_times = [v for v in times_to_plot if not np.isnan(v)]
                    ax.set_ylim([max(0, min(valid_times) - 1), min(24, max(valid_times) + 1)])
                else:
                    ax.set_ylim([6.5, 10])
            else:
                overtime_count = 0
                undertime_count = 0
                times_to_plot = []
                for day in days:
                    values = log_data[day]["time_out"]
                    if values:
                        latest = max(values)  # latest time out
                        times_to_plot.append(float(latest))
                        if latest >= 17.0:  # standard 5PM threshold
                            overtime_count += 1
                        else:
                            undertime_count += 1
                    else:
                        times_to_plot.append(np.nan)

                tk.Label(stats_content_frame, text=f"Overtime/On-time: {overtime_count}", bg="#1da22a", fg="white").pack(fill="x", pady=4)
                tk.Label(stats_content_frame, text=f"Undertime: {undertime_count}", bg="#b31616", fg="white").pack(fill="x", pady=4)

                total = overtime_count + undertime_count
                status = "NO DATA" if total == 0 else ("UNDERTIME" if undertime_count > overtime_count else "ON TIME")
                status_bg = "#d9534f" if status == "UNDERTIME" else "#5cb85c"
                if status == "NO DATA":
                    status_bg = "#555555"
                tk.Label(stats_content_frame, text=status, bg=status_bg, fg="white", font=("Arial", 11, "bold")).pack(fill="x", pady=10)

                lines = ax.plot(day_numbers, times_to_plot, marker="o", markersize=8, linewidth=3, color="#ff7f0e", label="Time Out")
                ax.set_title("Latest Time Out by Day", fontsize=14, fontweight="bold", pad=10)
                
                if any(not np.isnan(v) for v in times_to_plot):
                    valid_times = [v for v in times_to_plot if not np.isnan(v)]
                    ax.set_ylim([max(0, min(valid_times) - 1), min(24, max(valid_times) + 1)])
                else:
                    ax.set_ylim([15, 20])

            ax.set_xticks(day_numbers)
            ax.set_xticklabels(days, rotation=45, ha="right", fontsize=11)
            ax.set_ylabel("Time (24h)", fontsize=12, fontweight="bold")
            ax.tick_params(axis='y', labelsize=11)
            ax.grid(True, alpha=0.4, linestyle='--')
            ax.legend(fontsize=11)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=graph_frame)

            annot = ax.annotate("", xy=(0,0), xytext=(10,10), textcoords="offset points",
                                bbox=dict(boxstyle="round4,pad=.5", fc="white", ec="gray", lw=1),
                                arrowprops=dict(arrowstyle="-|>", connectionstyle="arc3,rad=-0.2", color="gray"))
            annot.set_visible(False)
            
            def hover(event):
                vis = annot.get_visible()
                if event.inaxes == ax and lines:
                    cont, ind = lines[0].contains(event)
                    if cont:
                        x_data, y_data = lines[0].get_data()
                        idx = ind["ind"][0]
                        annot.xy = (x_data[idx], y_data[idx])
                        text = f"Date: {days[idx]}\nTime: {y_data[idx]:.2f}"
                        annot.set_text(text)
                        annot.set_visible(True)
                        canvas.draw_idle()
                    else:
                        if vis:
                            annot.set_visible(False)
                            canvas.draw_idle()

            canvas.mpl_connect("motion_notify_event", hover)
            
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        update_graph_and_stats()

    def _begin_reenroll(self, employee_id):
        employee = get_employee(employee_id)
        if employee is None:
            messagebox.showerror("Re-enroll", "Employee not found.")
            return

        self._activate_employee_session(employee_id)
        self._show_section("biometric")
        self.start_enrollment()

    def _on_close(self):
        if self.cap is not None:
            self.cap.release()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    HRISApp().run()
