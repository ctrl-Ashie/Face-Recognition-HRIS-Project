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
from modern_ui import (
    ModernStyles,
    ModernButton,
    PrimaryButton,
    SecondaryButton,
    ModernCard,
    ModernLabel,
    ModernEntry,
    create_gradient_header,
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

BG_COLOR = "#eef2f7"
HEADER_COLOR = "#010066"
HEADER_DARK = "#00004d"
ACCENT_COLOR = "#caab2f"
ACCENT_HOVER = "#b89a28"
FORM_BG = "#ffffff"
CARD_SHADOW = "#d1d8e3"
LOGO_PATH = "BCLogo.png"

EMPLOYEE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,19}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class HRISApp:
    """Primary employee-facing app (auth, camera verification, attendance, and employee-scoped logs)."""

    def __init__(self):
        load_dotenv()
        init_db()

        self.window = tk.Tk()
        self.window.title("Bank of Commerce - Facial Authentication")
        self.window.geometry("800x620")
        self.window.minsize(700, 550)
        self.window.config(bg=BG_COLOR)
        
        self._setup_window_style()

        self.logo_img = None
        self.status_text = tk.StringVar(value="Welcome to Bank of Commerce - Employee Facial Authentication System")

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

    def _setup_window_style(self):
        try:
            self.window.tk.call("tk", "scaling", 1.2)
        except:
            pass

    def _create_header(self, parent):
        header = tk.Frame(parent, bg=HEADER_COLOR, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        header_canvas = tk.Canvas(header, bg=HEADER_COLOR, highlightthickness=0, height=70)
        header_canvas.pack(fill="x")
        header_canvas.update_idletasks()
        
        w = header_canvas.winfo_width()
        if w < 100:
            w = 1120
        
        for i in range(70):
            ratio = i / 70
            r = int(1 + (0 - 1) * ratio)
            g = int(0 + (0 - 0) * ratio)
            b = int(102 + (77 - 102) * ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            header_canvas.create_rectangle(0, i, w, i+1, fill=color, outline="")
        
        logo = self._get_logo()
        if logo is not None:
            header_canvas.create_image(20, 15, image=logo, anchor="nw")
        
        header_canvas.create_text(80, 22, text="BANK OF COMMERCE", fill="#ffffff", 
                                  font=("Segoe UI", 18, "bold"), anchor="w")
        header_canvas.create_text(80, 45, text="Employee Facial Authentication System", fill="#caab2f", 
                                  font=("Segoe UI", 11), anchor="w")
        
        self.session_badge = tk.Frame(header, bg="#c9302c", padx=12, pady=4)
        self.session_badge.place(relx=1.0, rely=0.5, anchor="e", x=-20)
        
        self.session_label = tk.Label(
            self.session_badge,
            text="NOT LOGGED IN",
            bg="#c9302c",
            fg="#ffffff",
            font=("Segoe UI", 9, "bold"),
        )
        self.session_label.pack()
        
        return header

    def _build_ui(self):
        main_container = tk.Frame(self.window, bg=BG_COLOR)
        main_container.pack(fill="both", expand=True)

        header = tk.Frame(main_container, bg=HEADER_COLOR)
        header.pack(fill="x")
        self._create_header(header)

        nav = tk.Frame(main_container, bg=BG_COLOR)
        nav.pack(fill="x", padx=15, pady=(12, 8))

        nav_bg = tk.Frame(nav, bg=FORM_BG, relief="solid", borderwidth=1, border=1)
        nav_bg.pack(side="left")

        self.section_buttons = {}
        btn_configs = [
            ("auth", "Employee Login / Signup"),
            ("biometric", "Biometric Workspace"),
            ("logs", "Employee Logs"),
        ]
        
        for i, (key, text) in enumerate(btn_configs):
            btn = self._create_nav_button(nav_bg, text, lambda k=key: self._show_section(k))
            btn.pack(side="left", padx=0, pady=0)
            self.section_buttons[key] = btn
            if key != "auth":
                btn.config(state="disabled")
            
            if i < len(btn_configs) - 1:
                sep = tk.Frame(nav_bg, bg="#d1d5db", width=1, height=35)
                sep.pack(side="left", fill="y", pady=5)

        logout_frame = tk.Frame(nav, bg=BG_COLOR)
        logout_frame.pack(side="right")
        
        self.logout_btn = self._create_action_button(
            logout_frame, "Logout", self._logout_employee, "#6c757d", "#ffffff"
        )
        self.logout_btn.config(state="disabled")

        self.section_container = tk.Frame(main_container, bg=BG_COLOR)
        self.section_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        self.section_frames = {
            "auth": tk.Frame(self.section_container, bg=BG_COLOR),
            "biometric": tk.Frame(self.section_container, bg=BG_COLOR),
            "logs": tk.Frame(self.section_container, bg=BG_COLOR),
        }

        self._build_auth_section(self.section_frames["auth"])
        self._build_biometric_section(self.section_frames["biometric"])
        self._build_logs_section(self.section_frames["logs"])

        self._show_section("auth")

        status_bar = tk.Frame(self.window, bg=HEADER_COLOR, padx=15, pady=10)
        status_bar.pack(side="bottom", fill="x")
        
        status_icon = tk.Label(status_bar, text="●", bg=HEADER_COLOR, fg="#caab2f", font=("Segoe UI", 8))
        status_icon.pack(side="left", padx=(0, 5))
        
        status_label = tk.Label(
            status_bar,
            textvariable=self.status_text,
            anchor="w",
            bg=HEADER_COLOR,
            fg="#ffffff",
            font=("Segoe UI", 10),
        )
        status_label.pack(side="left")

    def _create_nav_button(self, parent, text, command):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg="#f8f9fa",
            fg=HEADER_COLOR,
            activebackground=ACCENT_COLOR,
            activeforeground="#ffffff",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            borderwidth=0,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT_COLOR, fg="#ffffff"))
        btn.bind("<Leave>", lambda e: btn.config(bg="#f8f9fa", fg=HEADER_COLOR))
        return btn

    def _create_action_button(self, parent, text, command, bg_color, fg_color):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg=bg_color,
            fg=fg_color,
            activebackground="#5a6268",
            activeforeground="#ffffff",
            relief="flat",
            padx=20,
            pady=8,
            cursor="hand2",
            borderwidth=0,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT_COLOR))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg_color))
        return btn

    def _build_section_header(self, parent, icon, title, subtitle):
        header = tk.Frame(parent, bg=FORM_BG)
        header.pack(fill="x", pady=(0, 15))
        
        icon_label = tk.Label(header, text=icon, bg=FORM_BG, fg=ACCENT_COLOR, 
                             font=("Segoe UI", 24), width=3)
        icon_label.pack(side="left", padx=(0, 15))
        
        text_frame = tk.Frame(header, bg=FORM_BG)
        text_frame.pack(side="left", fill="x")
        
        title_label = tk.Label(text_frame, text=title, bg=FORM_BG, fg=HEADER_COLOR, 
                              font=("Segoe UI", 20, "bold"), anchor="w")
        title_label.pack(fill="x")
        
        subtitle_label = tk.Label(text_frame, text=subtitle, bg=FORM_BG, 
                                 fg="#6c757d", font=("Segoe UI", 11), anchor="w")
        subtitle_label.pack(fill="x")
        
        return header

    def _build_card(self, parent, title, icon="▸"):
        card = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1, border=1)
        card.pack(fill="x", pady=(0, 15))
        
        card_header = tk.Frame(card, bg=HEADER_COLOR)
        card_header.pack(fill="x")
        
        tk.Label(card_header, text=f"{icon}  {title}", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 12, "bold"), padx=15, pady=8, anchor="w").pack(fill="x")
        
        card_content = tk.Frame(card, bg=FORM_BG)
        card_content.pack(fill="x", padx=15, pady=15)
        
        return card, card_content

    def _build_auth_section(self, parent):
        main_card = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1)
        main_card.pack(fill="both", expand=True)
        
        main_header = tk.Frame(main_card, bg=HEADER_COLOR, padx=15, pady=10)
        main_header.pack(fill="x")
        
        tk.Label(main_header, text="👤  EMPLOYEE ACCOUNT", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 13, "bold")).pack(side="left")
        
        content = tk.Frame(main_card, bg=FORM_BG, padx=15, pady=12)
        content.pack(fill="both", expand=True)

        login_card = tk.Frame(content, bg=FORM_BG, relief="solid", borderwidth=1)
        login_card.pack(fill="x", pady=(0, 10))
        login_header = tk.Frame(login_card, bg=HEADER_COLOR, padx=10, pady=5)
        login_header.pack(fill="x")
        tk.Label(login_header, text="🔑  Login to Your Account", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        login_content = tk.Frame(login_card, bg=FORM_BG, padx=12, pady=10)
        login_content.pack(fill="x")

        self.login_id_var = tk.StringVar()
        self._build_form_field(login_content, "Employee ID", self.login_id_var)

        signup_card = tk.Frame(content, bg=FORM_BG, relief="solid", borderwidth=1)
        signup_card.pack(fill="x")
        signup_header = tk.Frame(signup_card, bg=HEADER_COLOR, padx=10, pady=5)
        signup_header.pack(fill="x")
        tk.Label(signup_header, text="📝  Create New Account", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        signup_content = tk.Frame(signup_card, bg=FORM_BG, padx=12, pady=10)
        signup_content.pack(fill="x")

        self.signup_vars = {
            "employee_id": tk.StringVar(),
            "full_name": tk.StringVar(),
            "department": tk.StringVar(),
            "role_position": tk.StringVar(),
            "contact_number": tk.StringVar(),
            "email": tk.StringVar(),
        }

        fields_frame = tk.Frame(signup_content, bg=FORM_BG)
        fields_frame.pack(fill="x")

        left_col = tk.Frame(fields_frame, bg=FORM_BG)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 8))
        
        right_col = tk.Frame(fields_frame, bg=FORM_BG)
        right_col.pack(side="left", fill="both", expand=True)

        self._build_form_field(left_col, "Employee ID", self.signup_vars["employee_id"])
        self._build_form_field(left_col, "Full Name", self.signup_vars["full_name"])
        self._build_form_field(left_col, "Department", self.signup_vars["department"])
        self._build_form_field(right_col, "Role / Position", self.signup_vars["role_position"])
        self._build_form_field(right_col, "Contact Number", self.signup_vars["contact_number"])
        self._build_form_field(right_col, "Email", self.signup_vars["email"])

        btn_row = tk.Frame(content, bg=FORM_BG)
        btn_row.pack(fill="x", pady=(12, 0))
        
        self._create_primary_button(btn_row, "Login", self._login_employee, 120).pack(side="left", padx=(0, 8))
        self._create_primary_button(btn_row, "Create Account", self._signup_employee, 140).pack(side="left")

    def _build_form_field(self, parent, label, var):
        row = tk.Frame(parent, bg=FORM_BG)
        row.pack(fill="x", pady=2)
        
        tk.Label(row, text=label, bg=FORM_BG, fg=HEADER_COLOR,
                font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w", pady=(0, 2))
        
        entry = tk.Entry(
            row, textvariable=var,
            font=("Segoe UI", 11), bg="#f8f9fa", fg=HEADER_COLOR,
            relief="solid", highlightthickness=1,
            highlightcolor=ACCENT_COLOR, highlightbackground="#d1d5db",
            insertbackground=HEADER_COLOR, bd=2
        )
        entry.pack(fill="x", ipady=5)

    def _create_primary_button(self, parent, text, command, width=None):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 11, "bold"),
            bg=ACCENT_COLOR,
            fg="#ffffff",
            activebackground=ACCENT_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=25,
            pady=8,
            cursor="hand2",
            borderwidth=0,
        )
        if width:
            btn.config(width=width)
        btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=ACCENT_COLOR))
        return btn

    def _build_biometric_section(self, parent):
        left = tk.Frame(parent, bg=BG_COLOR)
        left.pack(side="left", fill="both", expand=True)

        right = tk.Frame(parent, bg=BG_COLOR)
        right.pack(side="right", fill="y", padx=(15, 0))

        cam_container = tk.Frame(left, bg="#1a1a2e", relief="solid", borderwidth=1)
        cam_container.pack(fill="both", expand=True, pady=(0, 15))
        
        self.cam_label = tk.Label(cam_container, bg="#1a1a2e", relief="flat")
        self.cam_label.pack(fill="both", expand=True, padx=0, pady=0)

        profile_card = tk.Frame(left, bg=FORM_BG, relief="solid", borderwidth=1)
        profile_card.pack(fill="x", pady=(0, 0))
        
        profile_header = tk.Frame(profile_card, bg=HEADER_COLOR, padx=12, pady=6)
        profile_header.pack(fill="x")
        tk.Label(profile_header, text="👤  SESSION PROFILE", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        
        self.profile_label = tk.Label(
            profile_card,
            text="No employee session active",
            font=("Segoe UI", 11),
            bg=FORM_BG,
            fg="#6c757d",
            justify="left",
            anchor="nw",
            padx=15,
            pady=12,
        )
        self.profile_label.pack(fill="x")

        enrollment_card = tk.Frame(right, bg=FORM_BG, relief="solid", borderwidth=1)
        enrollment_card.pack(fill="x", pady=(0, 15))
        
        enrollment_header = tk.Frame(enrollment_card, bg=HEADER_COLOR, padx=12, pady=6)
        enrollment_header.pack(fill="x")
        tk.Label(enrollment_header, text="📸  BIOMETRIC ENROLLMENT", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        
        enrollment_content = tk.Frame(enrollment_card, bg=FORM_BG, padx=15, pady=12)
        enrollment_content.pack(fill="x")
        
        tk.Label(enrollment_content, text="Use this for initial enrollment or re-enrollment of your facial data.",
                bg=FORM_BG, fg="#6c757d", font=("Segoe UI", 10), wraplength=260,
                justify="left").pack(anchor="w", pady=(0, 12))
        
        enroll_btn = self._create_primary_button(enrollment_content, "Start Face Enrollment", 
                                                 self.start_enrollment, 200)
        enroll_btn.pack(fill="x")

        attendance_card = tk.Frame(right, bg=FORM_BG, relief="solid", borderwidth=1)
        attendance_card.pack(fill="x", pady=(0, 15))
        
        attendance_header = tk.Frame(attendance_card, bg=HEADER_COLOR, padx=12, pady=6)
        attendance_header.pack(fill="x")
        tk.Label(attendance_header, text="⏱️  ATTENDANCE VERIFICATION", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        
        attendance_content = tk.Frame(attendance_card, bg=FORM_BG, padx=15, pady=12)
        attendance_content.pack(fill="x")
        
        tk.Label(attendance_content, text="Verify your identity for each attendance action.",
                bg=FORM_BG, fg="#6c757d", font=("Segoe UI", 10),
                justify="left").pack(anchor="w", pady=(0, 12))
        
        self._create_primary_button(attendance_content, "Verify and Time In",
            lambda: self.start_verification_for_action("TIME_IN"), 200).pack(fill="x", pady=(0, 8))
        
        self._create_primary_button(attendance_content, "Verify and Time Out",
            lambda: self.start_verification_for_action("TIME_OUT"), 200).pack(fill="x")

        status_card = tk.Frame(right, bg=FORM_BG, relief="solid", borderwidth=1)
        status_card.pack(fill="x", pady=(15, 0))
        
        status_header = tk.Frame(status_card, bg="#6c757d", padx=12, pady=6)
        status_header.pack(fill="x")
        tk.Label(status_header, text="📊  CAPTURE STATUS", bg="#6c757d", fg="#ffffff",
                font=("Segoe UI", 10, "bold")).pack(side="left")
        
        status_content = tk.Frame(status_card, bg=FORM_BG, padx=15, pady=12)
        status_content.pack(fill="x")
        
        self.mode_label = tk.Label(status_content, text="Mode: Idle", bg=FORM_BG, 
                                   fg=HEADER_COLOR, font=("Segoe UI", 11, "bold"))
        self.mode_label.pack(anchor="w", pady=(0, 8))

        self.capture_label = tk.Label(status_content, text=f"Captured: 0/{MAX_SAMPLES}", 
                                       bg=FORM_BG, fg="#6c757d", font=("Segoe UI", 10))
        self.capture_label.pack(anchor="w")

    def _build_logs_section(self, parent):
        main_card = tk.Frame(parent, bg=FORM_BG, relief="solid", borderwidth=1)
        main_card.pack(fill="both", expand=True)
        
        main_header = tk.Frame(main_card, bg=HEADER_COLOR, padx=15, pady=10)
        main_header.pack(fill="x")
        
        tk.Label(main_header, text="📋  EMPLOYEE ATTENDANCE LOGS", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 13, "bold")).pack(side="left")
        
        content = tk.Frame(main_card, bg=FORM_BG, padx=15, pady=15)
        content.pack(fill="both", expand=True)

        self.logs_scope_label = tk.Label(
            content,
            text="Your attendance records and statistics",
            bg=FORM_BG,
            fg="#6c757d",
            font=("Segoe UI", 11),
            anchor="w",
        )
        self.logs_scope_label.pack(anchor="w", pady=(0, 15))

        btn_frame = tk.Frame(content, bg=FORM_BG)
        btn_frame.pack(fill="x", pady=(0, 15))

        btn_style = {
            "font": ("Segoe UI", 10, "bold"),
            "relief": "flat",
            "cursor": "hand2",
            "pady": 10,
        }

        btn1 = tk.Button(btn_frame, text="📄  View User Logs", command=self.user_logs_clicked,
                        bg="#007bff", fg="#ffffff", **btn_style)
        btn1.pack(side="left", fill="x", expand=True, padx=(0, 8))
        btn1.bind("<Enter>", lambda e: btn1.config(bg="#0056b3"))
        btn1.bind("<Leave>", lambda e: btn1.config(bg="#007bff"))

        btn2 = tk.Button(btn_frame, text="⚠️  Error Logs", command=self.log_error_clicked,
                        bg="#dc3545", fg="#ffffff", **btn_style)
        btn2.pack(side="left", fill="x", expand=True, padx=(0, 8))
        btn2.bind("<Enter>", lambda e: btn2.config(bg="#c82333"))
        btn2.bind("<Leave>", lambda e: btn2.config(bg="#dc3545"))

        btn3 = tk.Button(btn_frame, text="📊  Attendance Summary", command=self.log_summary_clicked,
                        bg="#28a745", fg="#ffffff", **btn_style)
        btn3.pack(side="left", fill="x", expand=True)
        btn3.bind("<Enter>", lambda e: btn3.config(bg="#218838"))
        btn3.bind("<Leave>", lambda e: btn3.config(bg="#28a745"))
        
        info_label = tk.Label(content, text="ℹ️ View your attendance history, errors, and statistical graphs here.",
                             bg=FORM_BG, fg="#6c757d", font=("Segoe UI", 10))
        info_label.pack(anchor="w", pady=(20, 0))

    def _show_section(self, section):
        if section in {"biometric", "logs"} and not self.logged_in_employee_id:
            messagebox.showwarning("Employee Session", "Login first to access this section.")
            section = "auth"

        for key, frame in self.section_frames.items():
            if key == section:
                frame.pack(fill="both", expand=True)
                if key in self.section_buttons:
                    self.section_buttons[key].config(bg=ACCENT_COLOR, fg="#ffffff")
            else:
                frame.pack_forget()
                if key in self.section_buttons:
                    self.section_buttons[key].config(bg="#f8f9fa", fg=HEADER_COLOR)

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
        self.session_label.config(text="LOGGED IN")
        self.session_label.config(bg="#28a745")
        self.session_badge.config(bg="#28a745")
        self.logout_btn.config(state="normal")
        self.section_buttons["biometric"].config(state="normal")
        self.section_buttons["logs"].config(state="normal")
        self.logs_scope_label.config(text=f"Viewing logs for: {employee_id}")

        employee = get_employee(employee_id)
        if employee:
            self.profile_label.config(
                text=(
                    f"✓ SESSION ACTIVE\n\n"
                    f"ID: {employee['employee_id']}\n"
                    f"Name: {employee['full_name']}\n"
                    f"Dept: {employee['department']}\n"
                    f"Role: {employee['role_position']}"
                ),
                fg=HEADER_COLOR
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

        self.session_label.config(text="NOT LOGGED IN")
        self.session_label.config(bg="#c9302c")
        self.session_badge.config(bg="#c9302c")
        self.logout_btn.config(state="disabled")
        self.section_buttons["biometric"].config(state="disabled")
        self.section_buttons["logs"].config(state="disabled")
        self.logs_scope_label.config(text="Available only when employee is logged in.")
        self.profile_label.config(text="No employee session active", fg="#6c757d")

        self._show_section("auth")
        self._set_status("Employee logged out. Thank you for using Bank of Commerce!")

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
                    f"✓ VERIFIED FOR {action.replace('_', ' ')}\n\n"
                    f"ID: {self.logged_in_employee_id}\n"
                    f"Action: {action.replace('_', ' ')}\n"
                    f"Score: {float(result['score']):.3f}"
                ),
                fg="#28a745"
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

        header = tk.Frame(ulwindow, bg=HEADER_COLOR, padx=15, pady=10)
        header.pack(fill="x")
        tk.Label(header, text=f"📋 User Logs - {target_employee_id}", 
                bg=HEADER_COLOR, fg="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left")

        table_frame = tk.Frame(ulwindow, bg=BG_COLOR, padx=15, pady=15)
        table_frame.pack(fill="both", expand=True)

        headers = ["No.", "Day", "Time In", "Time Out"]
        
        for col, header_text in enumerate(headers):
            tk.Label(
                table_frame,
                text=header_text,
                font=("Segoe UI", 11, "bold"),
                bg=HEADER_COLOR,
                fg="white",
                padx=15,
                pady=10,
                relief="flat",
            ).grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
            table_frame.columnconfigure(col, weight=1)

        if not session_rows:
            tk.Label(table_frame, text="No logs found.", bg=FORM_BG,
                    font=("Segoe UI", 12), fg="#6c757d").grid(column=0, row=1, columnspan=4, sticky="nsew", pady=20)
            return

        for idx, session in enumerate(session_rows, start=1):
            row_data = [str(idx), session["day"], session["time_in"], session["time_out"]]
            row_bg = FORM_BG if idx % 2 == 1 else "#f8f9fa"
            for col_idx, cell_data in enumerate(row_data):
                tk.Label(
                    table_frame,
                    text=cell_data,
                    font=("Segoe UI", 11),
                    bg=row_bg,
                    fg=HEADER_COLOR,
                    padx=15,
                    pady=10,
                    relief="flat",
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

        header = tk.Frame(lewindow, bg=HEADER_COLOR, padx=15, pady=10)
        header.pack(fill="x")
        tk.Label(header, text=f"⚠️ Error Logs - {target_employee_id}", 
                bg=HEADER_COLOR, fg="#ffffff", font=("Segoe UI", 14, "bold")).pack(side="left")

        table_frame = tk.Frame(lewindow, bg=BG_COLOR, padx=15, pady=15)
        table_frame.pack(fill="both", expand=True)

        headers = ["No.", "Day", "Time", "Type"]
        for col, header_text in enumerate(headers):
            tk.Label(
                table_frame,
                text=header_text,
                font=("Segoe UI", 11, "bold"),
                bg=HEADER_COLOR,
                fg="white",
                padx=15,
                pady=10,
                relief="flat",
            ).grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
            table_frame.columnconfigure(col, weight=1)

        if not errors:
            tk.Label(table_frame, text="No error logs found.", bg=FORM_BG,
                    font=("Segoe UI", 12), fg="#6c757d").grid(column=0, row=1, columnspan=4, sticky="nsew", pady=20)
            return

        for idx, row in enumerate(errors, start=1):
            stamp = datetime.fromisoformat(row["timestamp"])
            row_data = [
                str(idx),
                stamp.strftime("%A"),
                stamp.strftime("%I:%M %p"),
                self._classify_error(row["message"]),
            ]
            row_bg = FORM_BG if idx % 2 == 1 else "#f8f9fa"
            for col_idx, cell_data in enumerate(row_data):
                tk.Label(
                    table_frame,
                    text=cell_data,
                    font=("Segoe UI", 11),
                    bg=row_bg,
                    fg=HEADER_COLOR,
                    padx=15,
                    pady=10,
                    relief="flat",
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
        lswindow.title(f"Attendance Summary - {target_employee_id}")
        lswindow.geometry("1000x650")
        lswindow.minsize(900, 550)
        lswindow.config(bg=BG_COLOR)

        header = tk.Frame(lswindow, bg=HEADER_COLOR, padx=20, pady=12)
        header.pack(fill="x")
        tk.Label(header, text="📊 Attendance Summary", bg=HEADER_COLOR, fg="#ffffff", 
                font=("Segoe UI", 16, "bold")).pack(side="left")

        view_state = {"current": "time_in"}

        btn_frame = tk.Frame(lswindow, bg=FORM_BG, padx=20, pady=12)
        btn_frame.pack(fill="x")

        time_in_btn = tk.Button(btn_frame, text="🕐  Time In Stats", bg=ACCENT_COLOR, fg="#ffffff", 
                               font=("Segoe UI", 12, "bold"), relief="flat", cursor="hand2",
                               command=lambda: update_view("time_in"), width=15, pady=8)
        time_in_btn.pack(side="left", padx=(0, 15))

        time_out_btn = tk.Button(btn_frame, text="🕑  Time Out Stats", bg="#6c757d", fg="#ffffff",
                               font=("Segoe UI", 12, "bold"), relief="flat", cursor="hand2",
                               command=lambda: update_view("time_out"), width=15, pady=8)
        time_out_btn.pack(side="left")

        for btn in [time_in_btn, time_out_btn]:
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=ACCENT_HOVER if b == time_in_btn else "#5a6268"))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=ACCENT_COLOR if b == time_in_btn else "#6c757d"))

        content_frame = tk.Frame(lswindow, bg=BG_COLOR)
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        graph_container = tk.Frame(content_frame, bg=FORM_BG, relief="solid", bd=1, width=700, height=450)
        graph_container.pack(side="left", fill="both", expand=True)
        graph_container.pack_propagate(False)

        stats_container = tk.Frame(content_frame, bg=FORM_BG, relief="solid", bd=1, width=220)
        stats_container.pack(side="right", fill="both", padx=(15, 0))
        stats_container.pack_propagate(False)

        stats_header = tk.Frame(stats_container, bg=HEADER_COLOR)
        stats_header.pack(fill="x")
        tk.Label(stats_header, text="📈 Quick Stats", bg=HEADER_COLOR, fg="#ffffff",
                font=("Segoe UI", 13, "bold"), pady=10).pack()

        stats_inner = tk.Frame(stats_container, bg=FORM_BG)
        stats_inner.pack(fill="both", expand=True, padx=15, pady=15)

        def update_view(view_type):
            view_state["current"] = view_type
            if view_type == "time_in":
                time_in_btn.config(bg=ACCENT_COLOR, fg="#ffffff")
                time_out_btn.config(bg="#6c757d", fg="#ffffff")
            else:
                time_in_btn.config(bg="#6c757d", fg="#ffffff")
                time_out_btn.config(bg=ACCENT_COLOR, fg="#ffffff")
            update_graph_and_stats()

        def update_graph_and_stats():
            for widget in graph_container.winfo_children():
                widget.destroy()
            for widget in stats_inner.winfo_children():
                widget.destroy()

            lswindow.update_idletasks()

            days = list(sorted(log_data.keys()))
            day_numbers = np.arange(len(days))
            fig = Figure(figsize=(6.5, 4.5))
            ax = fig.add_subplot(111)
            fig.patch.set_facecolor('#ffffff')

            if view_state["current"] == "time_in":
                early_count = 0
                late_count = 0
                times_to_plot = []
                for day in days:
                    values = log_data[day]["time_in"]
                    if values:
                        earliest = min(values)
                        times_to_plot.append(float(earliest))
                        if earliest <= 9.0:
                            early_count += 1
                        else:
                            late_count += 1
                    else:
                        times_to_plot.append(np.nan)

                on_time_card = tk.Frame(stats_inner, bg="#d4edda", relief="flat", bd=2)
                on_time_card.pack(fill="x", pady=(0, 8))
                tk.Label(on_time_card, text="✓ ON TIME", bg="#d4edda", fg="#155724",
                        font=("Segoe UI", 10, "bold"), pady=6).pack()
                tk.Label(on_time_card, text=str(early_count), bg="#d4edda", fg="#155724",
                        font=("Segoe UI", 28, "bold"), pady=(0, 8)).pack()

                late_card = tk.Frame(stats_inner, bg="#f8d7da", relief="flat", bd=2)
                late_card.pack(fill="x", pady=(0, 15))
                tk.Label(late_card, text="✗ LATE", bg="#f8d7da", fg="#721c24",
                        font=("Segoe UI", 10, "bold"), pady=6).pack()
                tk.Label(late_card, text=str(late_count), bg="#f8d7da", fg="#721c24",
                        font=("Segoe UI", 28, "bold"), pady=(0, 8)).pack()

                total = early_count + late_count
                status = "NO DATA" if total == 0 else ("LATE" if late_count > early_count else "ON TIME")
                status_bg = "#f8d7da" if status == "LATE" else "#d4edda"
                status_fg = "#721c24" if status == "LATE" else "#155724"
                if status == "NO DATA":
                    status_bg = "#e2e3e5"
                    status_fg = "#383d41"
                status_card = tk.Frame(stats_inner, bg=status_bg, relief="flat", bd=2)
                status_card.pack(fill="x", pady=(0, 0))
                tk.Label(status_card, text="OVERALL STATUS", bg=status_bg, fg=status_fg,
                        font=("Segoe UI", 9, "bold"), pady=5).pack()
                tk.Label(status_card, text=status, bg=status_bg, fg=status_fg,
                        font=("Segoe UI", 16, "bold"), pady=(0, 8)).pack()

                ax.plot(day_numbers, times_to_plot, marker="o", markersize=10, linewidth=3,
                       color="#007bff", label="Time In", markeredgecolor="#0056b3")
                ax.set_title("Time In by Day", fontsize=16, fontweight="bold", pad=15, color="#333333")
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
                        latest = max(values)
                        times_to_plot.append(float(latest))
                        if latest >= 17.0:
                            overtime_count += 1
                        else:
                            undertime_count += 1
                    else:
                        times_to_plot.append(np.nan)

                on_time_card = tk.Frame(stats_inner, bg="#d4edda", relief="flat", bd=2)
                on_time_card.pack(fill="x", pady=(0, 8))
                tk.Label(on_time_card, text="✓ OVERTIME", bg="#d4edda", fg="#155724",
                        font=("Segoe UI", 10, "bold"), pady=6).pack()
                tk.Label(on_time_card, text=str(overtime_count), bg="#d4edda", fg="#155724",
                        font=("Segoe UI", 28, "bold"), pady=(0, 8)).pack()

                late_card = tk.Frame(stats_inner, bg="#f8d7da", relief="flat", bd=2)
                late_card.pack(fill="x", pady=(0, 15))
                tk.Label(late_card, text="✗ EARLY OUT", bg="#f8d7da", fg="#721c24",
                        font=("Segoe UI", 10, "bold"), pady=6).pack()
                tk.Label(late_card, text=str(undertime_count), bg="#f8d7da", fg="#721c24",
                        font=("Segoe UI", 28, "bold"), pady=(0, 8)).pack()

                total = overtime_count + undertime_count
                status = "NO DATA" if total == 0 else ("EARLY OUT" if undertime_count > overtime_count else "ON TIME")
                status_bg = "#f8d7da" if status == "EARLY OUT" else "#d4edda"
                status_fg = "#721c24" if status == "EARLY OUT" else "#155724"
                if status == "NO DATA":
                    status_bg = "#e2e3e5"
                    status_fg = "#383d41"
                status_card = tk.Frame(stats_inner, bg=status_bg, relief="flat", bd=2)
                status_card.pack(fill="x", pady=(0, 0))
                tk.Label(status_card, text="OVERALL STATUS", bg=status_bg, fg=status_fg,
                        font=("Segoe UI", 9, "bold"), pady=5).pack()
                tk.Label(status_card, text=status, bg=status_bg, fg=status_fg,
                        font=("Segoe UI", 16, "bold"), pady=(0, 8)).pack()

                ax.plot(day_numbers, times_to_plot, marker="o", markersize=10, linewidth=3,
                       color="#28a745", label="Time Out", markeredgecolor="#1e7e34")
                ax.set_title("Time Out by Day", fontsize=16, fontweight="bold", pad=15, color="#333333")
                if any(not np.isnan(v) for v in times_to_plot):
                    valid_times = [v for v in times_to_plot if not np.isnan(v)]
                    ax.set_ylim([max(0, min(valid_times) - 1), min(24, max(valid_times) + 1)])
                else:
                    ax.set_ylim([15, 20])

            ax.set_facecolor('#f8f9fa')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#dee2e6')
            ax.spines['bottom'].set_color('#dee2e6')
            ax.tick_params(colors='#6c757d', labelsize=11)
            ax.set_xticks(day_numbers)
            ax.set_xticklabels([d[-5:] for d in days], rotation=45, ha="right", fontsize=10)
            ax.set_ylabel("Time (24h)", fontsize=12, color="#6c757d")
            ax.grid(True, alpha=0.4, color='#dee2e6')
            ax.legend(loc='upper right', fontsize=11)
            fig.tight_layout(pad=1.5)

            canvas = FigureCanvasTkAgg(fig, master=graph_container)
            fig.canvas.draw()
            canvas.get_tk_widget().place(relx=0, rely=0, relwidth=1, relheight=1)

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
