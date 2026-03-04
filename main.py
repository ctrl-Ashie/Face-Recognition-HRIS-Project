import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import cv2
from streamlit import columns, container
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

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
    
    table_frame = tk.Frame(ulwindow, bg="light gray")
    table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Configure grid columns
    table_frame.columnconfigure(0, weight=1)
    table_frame.columnconfigure(1, weight=1)
    table_frame.columnconfigure(2, weight=1)
    table_frame.columnconfigure(3, weight=1)
    
    # Create headers
    headers = ["No. of Logs", "Day", "Time In", "Time Out"]
    for col, header_text in enumerate(headers):
        header_lbl = tk.Label(
            table_frame,
            text=header_text,
            font=("Arial", 10, "bold"),
            bg="#b39306",
            fg="white",
            padx=10,
            pady=10,
            relief="ridge",
            borderwidth=2
        )
        header_lbl.grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
    
    # filler data - replace with actual log data in production
    sample_data = [
        ["1", "Monday", "08:00 AM", "05:00 PM"],
        ["2", "Tuesday", "08:15 AM", "05:30 PM"],
        ["3", "Wednesday", "08:00 AM", "05:00 PM"],
        ["4", "Thursday", "08:30 AM", "06:00 PM"],
    ]
    
    for row_idx, row_data in enumerate(sample_data, start=1):
        for col_idx, cell_data in enumerate(row_data):
            cell_lbl = tk.Label(
                table_frame,
                text=cell_data,
                font=("Arial", 10, "normal"),
                bg="white",
                fg="black",
                padx=10,
                pady=10,
                relief="solid",
                borderwidth=1
            )
            cell_lbl.grid(column=col_idx, row=row_idx, sticky="nsew", padx=2, pady=2)

def log_error_clicked():
    lewindow = tk.Toplevel(window)
    apply_design(lewindow, "Log Error")
    lewindow.minsize(700, 500)
    
    table_frame = tk.Frame(lewindow, bg="light gray")
    table_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Configure grid columns
    table_frame.columnconfigure(0, weight=1)
    table_frame.columnconfigure(1, weight=1)
    table_frame.columnconfigure(2, weight=1)
    
    # Create headers
    headers = ["No. of Error", "Day", "Time"]
    for col, header_text in enumerate(headers):
        header_lbl = tk.Label(
            table_frame,
            text=header_text,
            font=("Arial", 10, "bold"),
            bg="#1d1e5d",
            fg="white",
            padx=10,
            pady=10,
            relief="ridge",
            borderwidth=2
        )
        header_lbl.grid(column=col, row=0, sticky="nsew", padx=2, pady=2)
    
    # filler data - replace with actual log data in production
    sample_data = [
        ["1", "Monday", "08:00 AM"],
        ["2", "Tuesday", "08:15 AM"],
        ["3", "Wednesday", "08:00 AM"],
        ["4", "Thursday", "08:30 AM"],
    ]
    
    for row_idx, row_data in enumerate(sample_data, start=1):
        for col_idx, cell_data in enumerate(row_data):
            cell_lbl = tk.Label(
                table_frame,
                text=cell_data,
                font=("Arial", 10, "bold"),
                bg="light gray",
                fg="black",
                padx=10,
                pady=10,
                relief="solid",
                borderwidth=1
            )
            cell_lbl.grid(column=col_idx, row=row_idx, sticky="nsew", padx=2, pady=2)
            
def log_summary_clicked():
    lswindow = tk.Toplevel(window)
    apply_design(lswindow, "Log Summary")
    lswindow.minsize(800, 600)
    
    # Sample data for demonstration
    log_data = {
        "Monday": {"time_in": [8.0, 8.5, 8.2], "time_out": [17.0, 17.5, 17.2]},
        "Tuesday": {"time_in": [8.25, 8.3], "time_out": [17.3, 17.1]},
        "Wednesday": {"time_in": [8.0], "time_out": [17.0]},
        "Thursday": {"time_in": [8.5, 8.3, 8.1], "time_out": [18.0, 17.8, 17.5]},
        "Friday": {"time_in": [8.15], "time_out": [16.8]},
    }
    
    # View state
    view_state = {"current": "time_in"}
    
    # Create top frame for buttons
    button_frame = tk.Frame(lswindow, bg=BG_COLOR)
    button_frame.pack(side="top", fill="x", padx=10, pady=10)
    
    def update_view(view_type):
        view_state["current"] = view_type
        # Update button colors
        if view_type == "time_in":
            time_in_btn.config(relief="sunken", bg=ACCENT_COLOR)
            time_out_btn.config(relief="raised", bg=HEADER_COLOR)
        else:
            time_in_btn.config(relief="raised", bg=HEADER_COLOR)
            time_out_btn.config(relief="sunken", bg=ACCENT_COLOR)
        update_graph_and_stats()
    
    time_in_btn = tk.Button(
        button_frame,
        text="Time In",
        font=("Arial", 10, "bold"),
        bg=HEADER_COLOR,
        fg="white",
        padx=10,
        pady=5,
        command=lambda: update_view("time_in"),
        relief="sunken"
    )
    time_in_btn.pack(side="left", pady=5, padx=5)
    
    time_out_btn = tk.Button(
        button_frame,
        text="Time Out",
        font=("Arial", 10, "bold"),
        bg=HEADER_COLOR,
        fg="white",
        padx=10,
        pady=5,
        command=lambda: update_view("time_out")
    )
    time_out_btn.pack(side="left", pady=5, padx=5)
    
    content_frame = tk.Frame(lswindow, bg=BG_COLOR)
    content_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    # graph 
    graph_frame = tk.Frame(content_frame, bg="white", relief="solid", borderwidth=2)
    graph_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
    
    stats_frame = tk.Frame(content_frame, bg=FORM_BG, width=200)
    stats_frame.pack(side="right", fill="both", padx=0)
    stats_frame.pack_propagate(False)
    
    # Stats labels
    stats_title = tk.Label(
        stats_frame,
        text="Statistics",
        font=("Arial", 12, "bold"),
        bg=HEADER_COLOR,
        fg="white"
    )
    stats_title.pack(pady=5, padx=5, fill="x")
    
    stats_content_frame = tk.Frame(stats_frame, bg=FORM_BG)
    stats_content_frame.pack(fill="both", expand=True, padx=5, pady=5)
    
    status_frame = tk.Frame(stats_frame, bg=FORM_BG)
    status_frame.pack(fill="x", padx=5, pady=5)
    
    def update_graph_and_stats():
        for widget in graph_frame.winfo_children():
            widget.destroy()
        for widget in stats_content_frame.winfo_children():
            widget.destroy()
        for widget in status_frame.winfo_children():
            widget.destroy()
        
        #Conditions for time in and out
        if view_state["current"] == "time_in":
            early_count = 0
            late_count = 0
            for times in log_data.values():
                for time in times["time_in"]:
                    if time < 8.0:
                        early_count += 1
                    elif time > 8.0:
                        late_count += 1
            
            early_lbl = tk.Label(
                stats_content_frame,
                text=f"Early: {early_count}",
                font=("Arial", 11),
                bg="#106919",
                fg="white"
            )
            early_lbl.pack(pady=5, padx=5, fill="x")
            
            late_lbl = tk.Label(
                stats_content_frame,
                text=f"Late: {late_count}",
                font=("Arial", 11),
                bg="#8b221e",
                fg="white"
            )
            late_lbl.pack(pady=5, padx=5, fill="x")
            
            # Status indicator
            status_text = "Late" if late_count > early_count else "On Time"
            status_bg = "#9a2925" if late_count > early_count else "#5cb85c"
            status_lbl = tk.Label(
                status_frame,
                text=status_text,
                font=("Arial", 11, "bold"),
                bg=status_bg,
                fg="white",
                pady=5
            )
            status_lbl.pack(fill="x")
            
            fig = Figure(figsize=(5, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            days = list(log_data.keys())
            day_numbers = np.arange(len(days))
            
            # Calculate average time for each day
            avg_times = []
            for day in days:
                times = log_data[day]["time_in"]
                avg_times.append(np.mean(times))
            
            # Plot line graph
            ax.plot(day_numbers, avg_times, marker="o", linewidth=2, markersize=8, color=HEADER_COLOR)
            
            ax.set_xticks(day_numbers)
            ax.set_xticklabels(days, rotation=45)
            ax.set_ylabel("Time (24h format)", fontsize=9)
            ax.set_xlabel("Day", fontsize=9)
            ax.set_title("Time In by Day", fontsize=9, fontweight="bold")
            ax.grid(True, alpha=0.3)
            ax.set_ylim([7, 9])
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
         
         #Time out conditions   
        else:      
            overtime_count = 0
            undertime_count = 0
            exact_count = 0
            
            for times in log_data.values():
                for time in times["time_out"]:
                    if time > 17.0:
                        overtime_count += 1
                    elif time < 17.0:
                        undertime_count += 1
                    else:
                        exact_count += 1
            
            overtime_lbl = tk.Label(
                stats_content_frame,
                text=f"Overtime: {overtime_count}",
                font=("Arial", 11),
                bg="#1da22a",
                fg="white",
                relief="solid",
                borderwidth=1
            )
            
            undertime_lbl = tk.Label(
                stats_content_frame,
                text=f"Undertime: {undertime_count}",
                font=("Arial", 11),
                bg="#b31616",
                fg="white",
                relief="solid",
                borderwidth=1
            )
            
            exact_lbl = tk.Label(
                stats_content_frame,
                text=f"Exact: {exact_count}",
                font=("Arial", 11),
                bg=ACCENT_COLOR,
                fg="Black",
                relief="solid",
                borderwidth=1
            )
            exact_lbl.pack(pady=5, padx=5, fill="x")
            overtime_lbl.pack(pady=5, padx=5, fill="x")
            undertime_lbl.pack(pady=5, padx=5, fill="x")
            
            status_text = "Undertime" if undertime_count > overtime_count else "Overtime"
            status_bg = "#d9534f" if undertime_count > overtime_count else "#5cb85c"
            status_lbl = tk.Label(
                status_frame,
                text=status_text,
                font=("Arial", 11, "bold"),
                bg=status_bg,
                fg="white",
                pady=5
            )
            status_lbl.pack(fill="x")
            
            fig = Figure(figsize=(5, 4), dpi=100)
            ax = fig.add_subplot(111)
            
            days = list(log_data.keys())
            day_numbers = np.arange(len(days))
            
            # Calculate average time for each day
            avg_times = []
            for day in days:
                times = log_data[day]["time_out"]
                avg_times.append(np.mean(times))
            
            # Plot line graph
            ax.plot(day_numbers, avg_times, marker="o", linewidth=2, markersize=8, color=HEADER_COLOR)
            
            
            ax.set_xticks(day_numbers)
            ax.set_xticklabels(days, rotation=45)
            ax.set_ylabel("Time (24h format)", fontsize=10)
            ax.set_xlabel("Day", fontsize=10)
            ax.set_title("Time Out by Day", fontsize=12, fontweight="bold")
            ax.grid(True, alpha=0.3)
            ax.set_ylim([16, 18.5])
            fig.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
    
    update_graph_and_stats()

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

UserLogs = tk.Button(text="User Logs", command=user_logs_clicked,
                     width=15, height=2, bg=STATUS_BG, fg=STATUS_FG)
LogError = tk.Button(text="Log Error", command=log_error_clicked,
                     width=15, height=2, bg=STATUS_BG, fg=STATUS_FG)
LogSummary = tk.Button(text="Log Summary", command=log_summary_clicked,
                       width=15, height=2, bg=STATUS_BG, fg=STATUS_FG)




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