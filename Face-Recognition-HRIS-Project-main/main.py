import tkinter as tk
from collections import deque
from datetime import datetime

import cv2
from PIL import Image, ImageTk
import numpy as np

from Menu import AdminPanel

# --- shared design constants --------------------------------------------------
BG_COLOR = "light gray"
HEADER_COLOR = "#010066"
ACCENT_COLOR = "#caab2f"
FORM_BG = "#4e4d4d"
STATUS_BG = "#e1e1e1"
STATUS_FG = "#1f1f1f"
LOGO_PATH = "BCLogo.png"

_logo_img = None

def get_logo():
    global _logo_img
    if _logo_img is None:
        image = Image.open(LOGO_PATH)
        image = image.resize((44, 44), Image.Resampling.LANCZOS)
        _logo_img = ImageTk.PhotoImage(image)
    return _logo_img

def apply_design(win: tk.Toplevel | tk.Tk, title: str | None = None) -> tk.Frame:
    win.config(bg=BG_COLOR)
    if title:
        win.title(title)
    header = tk.Frame(win, bg=HEADER_COLOR, padx=8, pady=6)
    header.pack(side="top", fill="x")
    logo_lbl = tk.Label(header, image=get_logo(), bg=HEADER_COLOR)
    logo_lbl.pack(side="left")
    if title:
        title_lbl = tk.Label(
            header,
            text=title,
            font=("Times New Roman", 19, "bold"),
            bg=HEADER_COLOR,
            fg="white",
        )
        title_lbl.pack(side="left", padx=10)
    return header

# -----------------------------------------------------------------------------
from face_service import (
    DEFAULT_VERIFY_THRESHOLD,
    IMPOSTOR_MARGIN,
    MAX_SAMPLES,
    REQUIRED_VERIFY_FRAMES,
    build_employee_template,
    clear_employee_samples,
    get_face_region,
    has_enough_samples,
    save_face_sample,
    verify_claimed_employee,
    verifier_status,
)
from storage import (
    add_employee,
    can_log_action,
    employee_exists,
    get_daily_summary,
    get_employee,
    get_recent_attendance,
    get_recent_verification_errors,
    init_db,
    list_employees,
    log_attendance,
    log_verification,
)


if __name__ == "__main__":
    init_db()

    # Main window
    window = tk.Tk()
    header = apply_design(window, "Login Monitor")
    window.minsize(900, 600)
    window.config(bg="light gray")
    window.columnconfigure(0, weight=1)
    window.rowconfigure(1, weight=1)

    # Shared state
    status_var = tk.StringVar(value="System ready. Fill profile fields and start signup or verification.")
    verification_var = tk.StringVar(value="UNVERIFIED")

    verified_employee_id = None
    verified_score = None
    current_faces = []
    current_frame = None
    face_history = deque(maxlen=12)

    signup_active = False
    signup_data = None
    signup_count = 0
    last_signup_capture_ts = None
    signup_mode = "new"
    admin_panel = None


    def set_status(message):
        status_var.set(message)


    status_info = verifier_status()
    set_status(status_info["message"])


    def build_text_window(title, lines):
        child = tk.Toplevel(window)
        apply_design(child, title)
        child.geometry("900x550")
        text_box = tk.Text(child, wrap="word")
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", "\n".join(lines) if lines else "No records found.")
        text_box.config(state="disabled")


    def user_logs_clicked():
        rows = get_recent_attendance(limit=250)
        lines = ["Attendance Logs (latest first)", "-" * 90]
        for row in rows:
            lines.append(
                f"[{row['timestamp']}] {row['employee_id']} | {row['full_name'] or 'Unknown'} | {row['action']} | "
                f"Verified={bool(row['verified'])} | Score={row['score'] if row['score'] is not None else 'N/A'}"
            )
        build_text_window("User Logs", lines)


    def log_error_clicked():
        rows = get_recent_verification_errors(limit=250)
        lines = ["Verification Errors (latest first)", "-" * 90]
        for row in rows:
            lines.append(
                f"[{row['timestamp']}] Employee={row['employee_id'] or 'N/A'} | "
                f"Score={row['score'] if row['score'] is not None else 'N/A'} | {row['message']}"
            )
        build_text_window("Log Error", lines)


    def log_summary_clicked():
        rows = get_daily_summary()
        lines = ["Daily Attendance Summary", "-" * 70]
        for row in rows:
            lines.append(
                f"{row['day']} | Time In: {row['total_time_in']} | Time Out: {row['total_time_out']} | Total: {row['total_actions']}"
            )
        build_text_window("Log Summary", lines)


    def open_admin_panel():
        global admin_panel
        if admin_panel is not None and admin_panel.winfo_exists():
            admin_panel.lift()
            return
        # using apply_design inside panel so header shows correctly
        admin_panel = AdminPanel(window, on_status=set_status, on_reenroll=start_reenroll_for_employee)


    def update_verification_ui(verified, employee=None, score=None, message=None):
        global verified_employee_id, verified_score

        if verified and employee:
            verified_employee_id = employee["employee_id"]
            verified_score = score
            verification_var.set(f"VERIFIED: {employee['full_name']} ({employee['employee_id']})")
            verification_label.config(bg="#2e8b57")
            profile_value.config(
                text=(
                    f"ID: {employee['employee_id']}\n"
                    f"Name: {employee['full_name']}\n"
                    f"Dept: {employee['department']}\n"
                    f"Role: {employee['role_position']}\n"
                    f"Contact: {employee['contact_number']}\n"
                    f"Email: {employee['email']}\n"
                    f"Match Score: {score:.3f}"
                )
            )
            set_status(message or "Identity verified.")
        else:
            verified_employee_id = None
            verified_score = None
            verification_var.set("UNVERIFIED")
            verification_label.config(bg="#caab2f")
            profile_value.config(text="No verified employee.")
            set_status(message or "Identity not verified.")


    def create_entry_row(parent, row, label_text):
        tk.Label(parent, text=label_text, width=12, anchor="w", bg="#4e4d4d", fg="white").grid(
            row=row, column=0, sticky="w", padx=(0, 8), pady=2
        )
        entry = tk.Entry(parent)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        return entry


    def _read_form_values():
        employee_id = entry_employee_id.get().strip()
        full_name = entry_full_name.get().strip()
        department = entry_department.get().strip()
        role_position = entry_role.get().strip()
        contact_number = entry_contact.get().strip()
        email = entry_email.get().strip()
        return {
            "employee_id": employee_id,
            "full_name": full_name,
            "department": department,
            "role_position": role_position,
            "contact_number": contact_number,
            "email": email,
        }


    def _fill_form_from_employee(employee):
        entry_employee_id.delete(0, "end")
        entry_employee_id.insert(0, employee["employee_id"])
        entry_full_name.delete(0, "end")
        entry_full_name.insert(0, employee["full_name"])
        entry_department.delete(0, "end")
        entry_department.insert(0, employee["department"])
        entry_role.delete(0, "end")
        entry_role.insert(0, employee["role_position"])
        entry_contact.delete(0, "end")
        entry_contact.insert(0, employee["contact_number"])
        entry_email.delete(0, "end")
        entry_email.insert(0, employee["email"])


    def start_signup():
        global signup_active, signup_data, signup_count, last_signup_capture_ts, signup_mode

        form = _read_form_values()
        if not all(form.values()):
            set_status("Please fill in all signup fields before enrollment.")
            return

        if employee_exists(form["employee_id"]):
            set_status("Employee ID already exists. Use a unique ID.")
            return

        clear_employee_samples(form["employee_id"])
        signup_active = True
        signup_data = form
        signup_mode = "new"
        signup_count = 0
        last_signup_capture_ts = None
        set_status("Signup started. Keep one face centered until 10 valid samples are captured.")


    def start_reenroll_for_employee(employee_id):
        global signup_active, signup_data, signup_count, last_signup_capture_ts, signup_mode

        employee = get_employee(employee_id)
        if employee is None:
            set_status("Re-enrollment failed: employee not found.")
            return

        _fill_form_from_employee(employee)
        clear_employee_samples(employee_id)
        signup_active = True
        signup_data = employee
        signup_mode = "reenroll"
        signup_count = 0
        last_signup_capture_ts = None
        set_status(f"Re-enrollment started for {employee_id}. Capture 10 valid samples.")


    def stop_signup():
        global signup_active, signup_data, signup_count, last_signup_capture_ts, signup_mode
        signup_active = False
        signup_data = None
        signup_count = 0
        last_signup_capture_ts = None
        signup_mode = "new"
        set_status("Signup/Re-enrollment canceled.")


    def get_single_face_roi():
        if current_frame is None:
            return None, "No camera frame available."
        if len(current_faces) == 0:
            return None, "No face detected. Please face the camera."
        if len(current_faces) > 1:
            return None, "Multiple faces detected. Only one face is allowed."
        roi = get_face_region(current_frame, current_faces[0])
        if roi is None:
            return None, "Unable to isolate face region."
        return roi, None


    def is_face_quality_good(face_bgr, return_reason=False):
        if face_bgr is None:
            return (False, "No face") if return_reason else False
        h, w = face_bgr.shape[:2]
        if h < 60 or w < 60:
            return (False, "Face too small") if return_reason else False

        gray = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        blur_metric = cv2.Laplacian(gray, cv2.CV_64F).var()
        brightness = float(np.mean(gray))
        if blur_metric < 40:
            return (False, f"Too blurry ({blur_metric:.0f})") if return_reason else False
        if brightness < 35 or brightness > 225:
            return (False, f"Bad light ({brightness:.0f})") if return_reason else False
        return (True, "OK") if return_reason else True


    def verify_identity():
        employee_id = entry_employee_id.get().strip()
        if not employee_id:
            update_verification_ui(False, message="Enter Employee ID for verification.")
            log_verification(None, False, None, "Verification failed: missing employee ID")
            return

        employee = get_employee(employee_id)
        if employee is None:
            update_verification_ui(False, message="Employee ID not found.")
            log_verification(employee_id, False, None, "Verification failed: unknown employee ID")
            return

        if not has_enough_samples(employee_id):
            update_verification_ui(False, message="Employee does not have enough enrolled face samples.")
            log_verification(employee_id, False, None, "Verification failed: insufficient enrollment samples")
            return

        valid_faces = [crop for crop in list(face_history) if is_face_quality_good(crop)]
        if len(valid_faces) < REQUIRED_VERIFY_FRAMES:
            update_verification_ui(
                False,
                message=f"Need at least {REQUIRED_VERIFY_FRAMES} recent good face frames. Hold steady and retry.",
            )
            log_verification(employee_id, False, None, "Verification failed: insufficient good frames")
            return

        all_ids = [row["employee_id"] for row in list_employees()]
        result = verify_claimed_employee(
            employee_id,
            valid_faces,
            all_ids,
            threshold=DEFAULT_VERIFY_THRESHOLD,
            impostor_margin=IMPOSTOR_MARGIN,
            required_frames=REQUIRED_VERIFY_FRAMES,
        )

        if result["matched"]:
            msg = (
                f"Identity verified ({result['frames_passed']}/{result['frames_total']} frames passed). "
                f"Impostor score ceiling: {result['best_other']:.3f}"
            )
            update_verification_ui(True, employee=employee, score=result["score"], message=msg)
            log_verification(employee_id, True, result["score"], result["reason"])
        else:
            fail_message = (
                f"Verification failed. Score={result['score']:.3f}, "
                f"Best other={result['best_other']:.3f}, "
                f"Frames={result['frames_passed']}/{result['frames_total']}"
            )
            update_verification_ui(False, message=fail_message)
            log_verification(employee_id, False, result["score"], result["reason"])


    def handle_attendance(action):
        if verified_employee_id is None:
            set_status("Please verify identity before logging attendance.")
            return

        allowed, reason = can_log_action(verified_employee_id, action)
        if not allowed:
            set_status(reason)
            return

        log_attendance(verified_employee_id, action, True, verified_score)
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        set_status(f"{action.replace('_', ' ')} recorded for {verified_employee_id} at {now_text}.")


    def process_signup_capture(frame):
        global signup_active, signup_data, signup_count, last_signup_capture_ts, signup_mode
        if not signup_active or signup_data is None:
            return
        if len(current_faces) != 1:
            return

        now = datetime.now()
        if last_signup_capture_ts is not None:
            delta_ms = (now - last_signup_capture_ts).total_seconds() * 1000
            if delta_ms < 350:
                return

        roi = get_face_region(frame, current_faces[0])
        if not is_face_quality_good(roi):
            return

        signup_count += 1
        save_face_sample(signup_data["employee_id"], roi, signup_count)
        last_signup_capture_ts = now
        set_status(f"Capturing face samples: {signup_count}/{MAX_SAMPLES}")

        if signup_count >= MAX_SAMPLES:
            employee_id = signup_data["employee_id"]
            employee_name = signup_data["full_name"]

            if signup_mode == "new":
                add_employee(
                    signup_data["employee_id"],
                    signup_data["full_name"],
                    signup_data["department"],
                    signup_data["role_position"],
                    signup_data["contact_number"],
                    signup_data["email"],
                )

            try:
                build_employee_template(employee_id)
            except Exception as ex:
                signup_active = False
                signup_data = None
                signup_mode = "new"
                set_status(f"Enrollment capture completed but template build failed for {employee_id}: {ex}. Please re-enroll.")
                return

            signup_active = False
            signup_data = None
            signup_mode = "new"
            set_status(f"Enrollment complete for {employee_name} ({employee_id}).")


    def update_camera():
        global current_faces, current_frame

        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (CAM_W, CAM_H))
            current_frame = frame.copy()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            current_faces = list(faces)

            if len(faces) == 1:
                roi = get_face_region(current_frame, faces[0])
                if roi is not None and is_face_quality_good(roi):
                    face_history.append(roi)

            grid_color = (128, 0, 0)
            for i in range(1, 3):
                x = int(CAM_W * i / 3)
                cv2.line(frame, (x, 0), (x, CAM_H), grid_color, 1)
            for i in range(1, 3):
                y = int(CAM_H * i / 3)
                cv2.line(frame, (0, y), (CAM_W, y), grid_color, 1)

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Show quality feedback during signup
            quality_msg = ""
            if signup_active and signup_data is not None:
                cv2.putText(
                    frame,
                    f"ENROLLING: {signup_count}/{MAX_SAMPLES}",
                    (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (0, 255, 255),
                    2,
                )
                if len(current_faces) == 0:
                    quality_msg = "No face detected"
                elif len(current_faces) > 1:
                    quality_msg = "Multiple faces - need only one"
                else:
                    roi = get_face_region(current_frame, current_faces[0])
                    _, reason = is_face_quality_good(roi, return_reason=True)
                    if reason != "OK":
                        quality_msg = reason
                process_signup_capture(current_frame)

            if quality_msg:
                cv2.putText(
                    frame,
                    quality_msg,
                    (10, CAM_H - 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )

            if verified_employee_id:
                cv2.putText(
                    frame,
                    f"VERIFIED: {verified_employee_id}",
                    (10, CAM_H - 14),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.68,
                    (0, 255, 0),
                    2,
                )

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            cam_label.imgtk = imgtk
            cam_label.configure(image=imgtk)

        window.after(30, update_camera)


    def on_close():
        cap.release()
        window.destroy()

    header_buttons = tk.Frame(header, bg=HEADER_COLOR)
    header_buttons.pack(side="right")
    tk.Button(header_buttons, text="User Logs", command=user_logs_clicked).pack(side="left", padx=3)
    tk.Button(header_buttons, text="Log Error", command=log_error_clicked).pack(side="left", padx=3)
    tk.Button(header_buttons, text="Summary", command=log_summary_clicked).pack(side="left", padx=3)
    tk.Button(header_buttons, text="Admin Panel", command=open_admin_panel).pack(side="left", padx=3)

    content_frame = tk.Frame(window, bg="light gray", padx=10, pady=10)
    content_frame.pack(side="top", fill="both", expand=True)
    content_frame.columnconfigure(0, weight=3)
    content_frame.columnconfigure(1, weight=2)
    content_frame.rowconfigure(0, weight=1)

    # Camera container: use flat relief and zero border to avoid a visible black outline
    camera_frame = tk.Frame(content_frame, bg="black", bd=0, relief="flat")
    camera_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
    camera_frame.columnconfigure(0, weight=1)
    camera_frame.rowconfigure(0, weight=1)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(0)
    ret, test_frame = cap.read()
    if ret:
        native_h, native_w = test_frame.shape[:2]
    else:
        native_w, native_h = 700, 700

    CAM_W = 600
    CAM_H = int(CAM_W * native_h / native_w)
    # label showing camera image; remove highlight/border thickness to avoid frame border
    cam_label = tk.Label(camera_frame, bg="black", bd=0, highlightthickness=0)
    cam_label.grid(row=0, column=0, sticky="nsew")

    side_frame = tk.Frame(content_frame, bg="#4e4d4d", bd=2, relief="ridge")
    side_frame.grid(row=0, column=1, sticky="nsew")
    side_frame.columnconfigure(0, weight=1)

    verification_label = tk.Label(
        side_frame,
        textvariable=verification_var,
        font=("Arial", 12, "bold"),
        bg="#caab2f",
        fg="white",
        height=2,
    )
    verification_label.grid(row=0, column=0, sticky="ew")

    profile_value = tk.Label(
        side_frame,
        text="No verified employee.",
        justify="left",
        anchor="w",
        bg="#4e4d4d",
        fg="white",
    )
    profile_value.grid(row=1, column=0, sticky="ew", padx=10, pady=(8, 4))

    form_frame = tk.Frame(side_frame, bg="#4e4d4d")
    form_frame.grid(row=2, column=0, sticky="ew", padx=10)
    form_frame.columnconfigure(1, weight=1)

    entry_employee_id = create_entry_row(form_frame, 0, "Employee ID")
    entry_full_name = create_entry_row(form_frame, 1, "Full Name")
    entry_department = create_entry_row(form_frame, 2, "Department")
    entry_role = create_entry_row(form_frame, 3, "Role")
    entry_contact = create_entry_row(form_frame, 4, "Contact")
    entry_email = create_entry_row(form_frame, 5, "Email")

    button_group = tk.Frame(side_frame, bg="#4e4d4d")
    button_group.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
    button_group.columnconfigure(0, weight=1)
    button_group.columnconfigure(1, weight=1)

    tk.Button(button_group, text="Start Signup", command=start_signup).grid(row=0, column=0, sticky="ew", padx=(0, 4), pady=2)
    tk.Button(button_group, text="Cancel Signup", command=stop_signup).grid(row=0, column=1, sticky="ew", padx=(4, 0), pady=2)
    tk.Button(button_group, text="Verify Identity", command=verify_identity).grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=2)
    tk.Button(button_group, text="Clear Verification", command=lambda: update_verification_ui(False)).grid(
        row=1, column=1, sticky="ew", padx=(4, 0), pady=2
    )
    tk.Button(button_group, text="Time In", command=lambda: handle_attendance("TIME_IN")).grid(
        row=2, column=0, sticky="ew", padx=(0, 4), pady=2
    )
    tk.Button(button_group, text="Time Out", command=lambda: handle_attendance("TIME_OUT")).grid(
        row=2, column=1, sticky="ew", padx=(4, 0), pady=2
    )

    security_hint = tk.Label(
        side_frame,
        text="Security mode: local multi-frame verification with quality and impostor checks.",
        bg="#4e4d4d",
        fg="#ffd27d",
        justify="left",
        wraplength=320,
    )
    security_hint.grid(row=4, column=0, sticky="ew", padx=10, pady=(4, 8))

    status_label = tk.Label(
        window,
        textvariable=status_var,
        anchor="w",
        justify="left",
        bg="#e1e1e1",
        fg="#1f1f1f",
        relief="sunken",
        padx=8,
    )
    status_label.pack(side="bottom", fill="x")

    window.protocol("WM_DELETE_WINDOW", on_close)
    update_camera()
    window.mainloop()
    
    #end
