import tkinter as tk
from tkinter import PhotoImage
from PIL import Image, ImageTk
import cv2


# Create the main window
window = tk.Tk()
window.title("Login Monitor")
window.minsize(700, 500)
window.config(bg="light gray")

#Header
font_py = ("Times New Roman", 19, "bold")
first_label = tk.Label(text="Login Monitor", font=font_py, bg="navy blue", fg="white", width=50, height=2)
first_label.grid(column=0, row=0, columnspan=2)

my_logo = "BCLogo.png"
image = Image.open(my_logo)
image = image.resize((50, 50), Image.Resampling.LANCZOS)
Logo = ImageTk.PhotoImage(image)

logo_label = tk.Label(window, image=Logo)
logo_label.grid(column=0, row=1, padx=20, pady=20)
logo_label.place(x=20, y=5)
logo_label.image = Logo 

# Create the menu button

def user_logs_clicked():
    ulwindow = tk.Toplevel(window)
    ulwindow.title("User Logs")
    ulwindow.minsize(700, 500)
    window.config(bg="light gray") 

def log_error_clicked():
    lewindow = tk.Toplevel(window)
    lewindow.title("Log Error")
    lewindow.minsize(700, 500)
    window.config(bg="light gray")
    
def log_summary_clicked():
    lswindow = tk.Toplevel(window)
    lswindow.title("Log Summary")
    lswindow.minsize(700, 500)
    window.config(bg="light gray")

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

def update_camera():
    ret, frame = cap.read()
    if ret:
        frame = cv2.resize(frame, (CAM_W, CAM_H))
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