import tkinter as tk
from tkinter import messagebox
import cv2
from UI import UI

class Main(UI):
    def __init__(self):
        super().__init__()
        self.main.title("Bank of Commerce - Employee Facial Authentication System")
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        self.cap = cv2.VideoCapture(0)
        self.cam_label = None
        self.cam_w = 450
        self.cam_h = 338
        self.content_frame = tk.Frame(self.form_frame, bg=self.BG_COLOR)
        self._create_top_menu()
        self.content_frame.pack(fill="both", expand=True)

    def _create_top_menu(self):
        self.tab_bar = UI.TabBar(
            self.form_frame,
            tabs=["Register Face", "Log Face", "Attendance Logs", "Error Logs", "Log Summary", "Logout"],
            command=self._on_tab_change
        )
        self.tab_bar.pack(fill="x")

    def _on_tab_change(self, tab):
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        self.cam_label = None

        if tab == "Register Face":
            self.capture_face()
        elif tab == "Log Face":
            self.log_face()
        elif tab == "Attendance Logs":
            self.view_attendance()
        elif tab == "Error Logs":
            self.error_logs()
        elif tab == "Log Summary":
            self.view_log_summary()
        elif tab == "Logout":
            self.logout()

    def _show_camera(self, parent=None):
        container = parent or self.content_frame
        self.cam_label = tk.Label(container, bg="black")
        self.cam_label.pack(side="left", pady=10, padx=20)
        ret, frame = self.cap.read()
        if ret:
            h, w = frame.shape[:2]
            self.cam_ratio = h / w
        else:
            self.cam_ratio = 338 / 450
        self.cam_w = 450
        self.cam_h = int(self.cam_w * self.cam_ratio)
        self.cam_label.config(width=self.cam_w, height=self.cam_h)
        self._update_camera()
        
        container.bind("<Configure>", self._on_camera_resize)

    def _on_camera_resize(self, event):
        new_w = int(event.width * 0.65)
        if new_w < 100:
            return
        self.cam_w = new_w
        self.cam_h = int(self.cam_w * self.cam_ratio)
        if self.cam_label and self.cam_label.winfo_exists():
            self.cam_label.config(width=self.cam_w, height=self.cam_h)

    def _update_camera(self):
        if self.cam_label is None or not self.cam_label.winfo_exists():
            return
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.resize(frame, (self.cam_w, self.cam_h))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = tk.PhotoImage(data=cv2.imencode('.ppm', frame)[1].tobytes())
            self.cam_label.config(image=img)
            self.cam_label.image = img
        self.main.after(30, self._update_camera)

    def capture_face(self):
        outer = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True)

        self._show_camera(parent=outer)
        right = tk.Frame(outer, bg=self.BG_COLOR)
        right.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=15)

        UI.EnrollmentCard(
            right,
            title="BIOMETRIC ENROLLMENT",
            description="Use this for initial enrollment or re-enrollment of your facial data."
        ).pack(side="top", fill="x")  
        UI.RoundedButton(right, text="Capture Face", command=self._get_face_image).pack(pady=(10, 5))
        
    def _get_face_image(self):
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Error", "Failed to capture image from camera.")
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            messagebox.showwarning("No Face Detected", "No face detected. Please try again.")
            return None
        x, y, w, h = faces[0]
        messagebox.showinfo("Face Captured", "Face captured successfully.")
        return frame[y:y+h, x:x+w]
        
    def log_face(self):
        outer = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True)

        self._show_camera(parent=outer)

        right = tk.Frame(outer, bg=self.BG_COLOR)
        right.pack(side="right", fill="both", expand=True, padx=(0, 20), pady=15) 
        
        UI.EnrollmentCard(
            right,
            title="ATTEMPTING LOGIN",
            description="Use this for logging your face."
        ).pack(side="top", fill="x")

        UI.RoundedButton(right, text="Time In", command=self._log_attendance, bg="#28a745").pack(pady=(10, 5))
        UI.RoundedButton(right, text="Time Out", command=self._log_attendance, bg="#dc3545").pack(pady=5)
        
    def _log_attendance(self):
        messagebox.showinfo("Attendance Logged", "Your attendance has been logged successfully.")
        
    def view_attendance(self):
        
        log = UI.log_frame(self.content_frame)
        log.pack(fill="both", expand=True)
        rows = [
            ("1", "6:07AM",  "08:00 AM"),
            ("2", "8:05AM",  "05:00 PM"),
            ("3", "9:00PM",  "08:15 AM"),
        ]

        for i, row in enumerate(rows):
            tag = "odd" if i % 2 == 0 else "even"
            log.my_log.insert("", "end", values=row, tags=(tag,))
            
    def error_logs(self):
        log = UI.error_frame(self.content_frame)
        log.pack(fill="both", expand=True)

        # sample data 
        rows = [
            ("1",   "08:00 AM", "invalid login attempt"),
            ("2", "05:00 PM", "failed face recognition"),
            ("3", "08:15 AM", "database connection error"),
        ]

        for i, row in enumerate(rows):
            tag = "odd" if i % 2 == 0 else "even"
            log.my_log.insert("", "end", values=row, tags=(tag,))
            
    def view_log_summary(self):
        outer = tk.Frame(self.content_frame, bg=self.BG_COLOR)
        outer.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(outer, text="Attendance Summary", bg=self.BG_COLOR,
                fg=UI.HEADER_COLOR, font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))

        rows = [
            ("Mon", "6:07AM", "5:00 PM"),
            ("Tue", "8:05AM", "5:00 PM"),
            ("Wed", "9:00AM", "5:15 PM"),
            ("Thu", "8:30AM", "4:45 PM"),
            ("Fri", "7:55AM", "5:00 PM"),
        ]

        # auto-generate summary from rows
        total_days   = len(rows)
        time_ins     = [r[1] for r in rows if r[1] and r[1] != "—"]
        time_outs    = [r[2] for r in rows if r[2] and r[2] != "—"]
        earliest_in  = min(time_ins)  if time_ins  else "N/A"
        latest_in    = max(time_ins)  if time_ins  else "N/A"
        earliest_out = min(time_outs) if time_outs else "N/A"
        latest_out   = max(time_outs) if time_outs else "N/A"

        summary = (f"Days Logged: {total_days}\n\n"
                f"Earliest Time In: {earliest_in}\n"
                f"Latest Time In:   {latest_in}\n\n"
                f"Earliest Time Out: {earliest_out}\n"
                f"Latest Time Out:   {latest_out}")

        content = tk.Frame(outer, bg=self.BG_COLOR)
        content.pack(fill="both", expand=True)

        # summary card on the right first
        right = tk.Frame(content, bg=self.BG_COLOR)
        right.pack(side="right", fill="y", padx=(10, 0), pady=5)

        UI.EnrollmentCard(
            right,
            title="WEEKLY SUMMARY",
            description=summary
        ).pack(fill="x")
        
        graph = UI.AttendanceGraph(content, rows=rows)
        graph.pack(side="left", fill="both", expand=True)

            
    def logout(self):
        self.cap.release()
        self.main.destroy()
        from Login import Login
        app = Login()
        app.main.mainloop()

if __name__ == "__main__":
    app = Main()
    app.main.mainloop()