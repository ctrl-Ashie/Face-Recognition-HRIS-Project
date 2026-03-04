import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import cv2

# --- design constants & helpers ------------------------------------------------
BG_COLOR = "light gray"
HEADER_COLOR = "#010066"
ACCENT_COLOR = "#caab2f"  # used for verification/status panels
FORM_BG = "#4e4d4d"
STATUS_BG = "#e1e1e1"
STATUS_FG = "#1f1f1f"
LOGO_PATH = "BCLogo.png"

_logo_img = None

def get_logo():
    """Load and cache the logo image used in headers."""
    global _logo_img
    if _logo_img is None:
        image = Image.open(LOGO_PATH)
        image = image.resize((44, 44), Image.Resampling.LANCZOS)
        _logo_img = ImageTk.PhotoImage(image)
    return _logo_img

def apply_design(win: tk.Tk | tk.Toplevel, title: str | None = None) -> tk.Frame:
    """Apply the shared color scheme + header/logo to any window.

    Returns the header frame so callers can add their own buttons without
    interfering with the layout.
    """
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

# ------------------------------------------------------------------------------


# Create the main window
window = tk.Tk()
apply_design(window, "Login Monitor")
window.minsize(700, 500)


Face_label = tk.Label(text="Verification", font=("Arial", 12, "bold"), bg=ACCENT_COLOR, fg="white", width=15, height=2)
Profile_label = tk.Label(text="Profile", font=("Arial", 12, "bold"), bg=FORM_BG, fg="white", width=15, height=16)

# menu button

def user_logs_clicked():
    ulwindow = tk.Toplevel(window)
    apply_design(ulwindow, "User Logs")
    ulwindow.minsize(700, 500)

def log_error_clicked():
    lewindow = tk.Toplevel(window)
    apply_design(lewindow, "Log Error")
    lewindow.minsize(700, 500)
def log_summary_clicked():
    lswindow = tk.Toplevel(window)
    apply_design(lswindow, "Log Summary")
    lswindow.minsize(700, 500)

def menu_clicked(  ):
    click = getattr(menu_button, "clicked", False)
    if click:
        menu_button.place(x=680, y=20)
        menu_button.clicked = False
        UserLogs.place_forget()
        LogError.place_forget()
        LogSummary.place_forget()
    else:
        menu_button.place(x=600, y=20)
        menu_button.clicked = True
        UserLogs.place(x=600, y=60)
        LogError.place(x=600, y=100)
        LogSummary.place(x=600, y=140)
menu_button = tk.Button(text="Menu",command=menu_clicked)
menu_button.place(x=680, y=20)
menu_button.clicked = False

UserLogs = tk.Button(text="User Logs", command=user_logs_clicked)
LogError = tk.Button(text="Log Error", command=log_error_clicked)
LogSummary = tk.Button(text="Log Summary", command=log_summary_clicked)




#Camera
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
cap = cv2.VideoCapture(0)

# Grab one frame to get native aspect ratio
ret, test_frame = cap.read()
if ret:
    native_h, native_w = test_frame.shape[:2]
else:
    native_w, native_h = 640, 480

CAM_W = 500
CAM_H = int(CAM_W * native_h / native_w)  # preserve aspect ratio

cam_label = tk.Label(window)
cam_label.place(x=50, y=90, width=CAM_W, height=CAM_H)

face_x = 50 + CAM_W + 20
face_y = 90
Face_label.place(x=face_x, y=face_y)

profile_x = face_x
profile_y = face_y + 50
Profile_label.place(x=profile_x, y=profile_y)

def update_camera():
    ret, frame = cap.read()
    if ret:
        frame = cv2.resize(frame, (CAM_W, CAM_H))

        grid_color = (128, 0, 0)
        for i in range(1, 3):
            x = int(CAM_W * i / 3)
            cv2.line(frame, (x, 0), (x, CAM_H), grid_color, 1)
        for i in range(1, 3):
            y = int(CAM_H * i / 3)
            cv2.line(frame, (0, y), (CAM_W, y), grid_color, 1)

        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))

        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        cam_label.imgtk = imgtk
        cam_label.configure(image=imgtk)

    window.after(30, update_camera)

def on_close():
    cap.release()
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)
update_camera()

window.mainloop()