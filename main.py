import tkinter as tk
window = tk.Tk()
window.title("Login Monitor")
window.minsize(700, 500)

font_py = ("Arial", 19, "bold")

first_label = tk.Label(text="Login Monitor", font=font_py)
first_label.pack(side="top")

def menu_clicked(  ):
    print("filler")
    

menu_button = tk.Button(text="Menu",command=menu_clicked)
menu_button.pack()

window.mainloop()