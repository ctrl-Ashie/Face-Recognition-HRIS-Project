
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

class UI:
    BG_COLOR = "#eef2f7"
    HEADER_COLOR = "#010066"
    HEADER_DARK = "#00004d"
    ACCENT_COLOR = "#caab2f"
    ACCENT_HOVER = "#b89a28"
    FORM_BG = "#ffffff"
    CARD_SHADOW = "#d1d8e3"
    LOGO_PATH = "BCLogo.png"
    
    def __init__(self):
        self.main = tk.Tk()
        self.main.title("Login Application")
        self.main.geometry("700x500")
        self.logo_img = None
        self.logo_ratio = None
        self._create_header(self.main)
        self.main.configure(bg=self.BG_COLOR)
        self.form_frame = tk.Frame(self.main, bg=self.BG_COLOR)
        self.form_frame.pack(fill="both", expand=True)
        
    def _create_header(self, parent):
        header = tk.Frame(parent, bg=self.HEADER_COLOR, height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        header_canvas = tk.Canvas(header, bg=self.HEADER_COLOR, highlightthickness=0, height=70)
        header_canvas.pack(fill="x")
        
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
                                  font=("Segoe UI", 11,"bold"), anchor="w")
        
        return header
    
    def _get_logo(self):
        if self.logo_img is not None:
            return self.logo_img

        try:
            image = Image.open(self.LOGO_PATH)
            width, height = image.size
            self.logo_ratio = f"{width/height:.2f}:1"
            image = image.resize((44, 44), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(image)
            return self.logo_img
        except Exception:
            return None

    class RoundedButton(tk.Canvas):
        def __init__(self, parent, text, command,
                     bg=None, fg=None, width=100, height=25, corner_radius=20, **kwargs):
            super().__init__(parent, width=width, height=height,
                             bg=parent.cget("bg"), highlightthickness=0, **kwargs)
           
            self.command       = command
            self.corner_radius = corner_radius
            self.bg            = bg or UI.ACCENT_COLOR 
            self.fg            = fg or "#ffffff"
            self.default_bg    = self.bg
            self.hover_bg      = self._darken_color(self.bg, 0.85)
            self.text          = text

            self._draw()
            self._bind_events()

        def _darken_color(self, hex_color, factor):
            hex_color = hex_color.lstrip("#")
            r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

        def _draw(self):
            self.delete("all")
            r = self.corner_radius
            w, h = int(self.cget("width")), int(self.cget("height"))
            self.create_rounded_rect(0, 0, w, h, r, fill=self.bg, outline="")
            self.create_text(w // 2, h // 2, text=self.text,
                             fill=self.fg, font=("Segoe UI", 10, "bold"))

        def create_rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
            self.create_polygon(
                x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
                x2, y2-r,  x2, y2,  x2-r, y2,  x1+r, y2,
                x1, y2,  x1, y2-r,  x1, y1+r,  x1, y1,
                smooth=True, **kwargs
            )

        def _bind_events(self):
            self.bind("<Enter>",    lambda e: self._on_hover(True))
            self.bind("<Leave>",    lambda e: self._on_hover(False))
            self.bind("<Button-1>", lambda e: self.command())

        def _on_hover(self, hovering):
            self.bg = self.hover_bg if hovering else self.default_bg
            self._draw()
            
    class login_header(tk.Frame):
        def __init__(self, parent):
            super().__init__(parent, bg=UI.HEADER_COLOR)
            self.pack(fill="x")
            
    class card(tk.Frame):
        def __init__(self, parent):
            super().__init__(parent, bg=UI.FORM_BG, highlightbackground=UI.CARD_SHADOW,
                             highlightthickness=1, bd=0)
            self.pack(pady=20, padx=40, fill="both", expand=True)
            
    class form(tk.Frame):
        def __init__(self, parent):
            super().__init__(parent, bg=UI.BG_COLOR)
            self.pack(fill="both", expand=True)
            
    class Entry(tk.Frame):
        def __init__(self, parent, textvariable=None, width=25, **kwargs):
            super().__init__(parent)
            self.config(bg=parent.cget("bg") if hasattr(parent, 'cget') else UI.FORM_BG)
            
            self._entry = tk.Entry(
                self,
                textvariable=textvariable,
                width=width,
                font=("Segoe UI", 10),
                bg=UI.FORM_BG,
                fg="#000000",
                relief="flat",
                highlightthickness=1,
                highlightcolor=UI.ACCENT_COLOR,
                highlightbackground=UI.CARD_SHADOW,
                insertbackground=UI.HEADER_COLOR,
            )
            self._entry.pack(fill="x", padx=8, pady=6)
            
            self.entry = self._entry
            
    class TabBar(tk.Frame):
        def __init__(self, parent, tabs: list, command=None, **kwargs):
            super().__init__(parent, bg="#ffffff", relief="solid", bd=1, **kwargs)
            self.command = command
            self.buttons = {}
            self.active_tab = None

            for i, label in enumerate(tabs):
                if i > 0:
                    tk.Frame(self, bg="#cccccc", width=1).pack(side="left", fill="y")

                btn = tk.Label(
                    self, text=label,
                    font=("Segoe UI", 10, "bold"),
                    fg="#333333",
                    bg="#ffffff",
                    padx=20, pady=12,
                    cursor="hand2"
                )
                btn.pack(side="left")
                btn.bind("<Button-1>", lambda e, l=label: self._on_click(l))
                btn.bind("<Enter>", lambda e, b=btn: self._on_hover(b, True))
                btn.bind("<Leave>", lambda e, b=btn, l=label: self._on_hover(b, False, l))
                self.buttons[label] = btn

            if tabs:
                self._on_click(tabs[0])

        def _on_click(self, label):
            for lbl, btn in self.buttons.items():
                btn.config(bg="#ffffff", fg="#000000")

            self.buttons[label].config(bg=UI.ACCENT_COLOR, fg="#ffffff")
            self.active_tab = label

            if self.command:
                self.command(label)

        def _on_hover(self, btn, entering, label=None):
            if label and label == self.active_tab:
                return
            btn.config(bg="#f0f0f0" if entering else "#ffffff")

    class EnrollmentCard(tk.Frame):
        def __init__(self, parent, title, description, **kwargs):
            super().__init__(parent, bg=UI.FORM_BG, relief="solid", borderwidth=1, **kwargs)
        
            header = tk.Frame(self, bg=UI.HEADER_COLOR, padx=12, pady=6)
            header.pack(fill="x")
            tk.Label(header, text=title, bg=UI.HEADER_COLOR, fg="#ffffff",
                 font=("Segoe UI", 10, "bold")).pack(side="left")

            content = tk.Frame(self, bg=UI.FORM_BG, padx=15, pady=12)
            content.pack(fill="x")
            tk.Label(content, text=description, bg=UI.FORM_BG, fg="#6c757d",
                     font=("Segoe UI", 10), wraplength=160, justify="left").pack(anchor="w", pady=(0, 12))
                
    class log_frame(tk.Frame):
        def __init__(self, parent):
            super().__init__(parent, bg=UI.FORM_BG)

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Custom.Treeview",
                            background=UI.FORM_BG,
                            foreground="#333333",
                            rowheight=30,
                            fieldbackground=UI.FORM_BG,
                            font=("Segoe UI", 10))
            style.configure("Custom.Treeview.Heading",
                            background=UI.HEADER_COLOR,
                            foreground="#ffffff",
                            font=("Segoe UI", 10, "bold"),
                            relief="flat")
            style.map("Custom.Treeview",
                    background=[("selected", UI.ACCENT_COLOR)],
                    foreground=[("selected", "#ffffff")])
            style.map("Custom.Treeview.Heading",
                    background=[("active", UI.HEADER_DARK)])

            my_log = ttk.Treeview(self,
                                columns=("No.","Time In", "Time Out"),  # ← match here
                                show="headings",
                                style="Custom.Treeview")
            my_log.heading("No.", text="No.")
            my_log.heading("Time In", text="Time In")
            my_log.heading("Time Out", text="Time Out")
            my_log.column("No.", width=50, anchor="center")
            my_log.column("Time In", width=150, anchor="center")
            my_log.column("Time Out", width=150, anchor="center")

            my_log.tag_configure("odd", background="#f5f7fa")
            my_log.tag_configure("even", background=UI.FORM_BG)

            my_log.pack(fill="both", expand=True, padx=10, pady=10)
            self.my_log = my_log 
    class error_frame(tk.Frame):
        def __init__(self, parent):
            super().__init__(parent, bg=UI.FORM_BG)

            style = ttk.Style()
            style.theme_use("clam")
            style.configure("Custom.Treeview",
                            background=UI.FORM_BG,
                            foreground="#333333",
                            rowheight=30,
                            fieldbackground=UI.FORM_BG,
                            font=("Segoe UI", 10))
            style.configure("Custom.Treeview.Heading",
                            background=UI.HEADER_COLOR,
                            foreground="#ffffff",
                            font=("Segoe UI", 10, "bold"),
                            relief="flat")
            style.map("Custom.Treeview",
                    background=[("selected", UI.ACCENT_COLOR)],
                    foreground=[("selected", "#ffffff")])
            style.map("Custom.Treeview.Heading",
                    background=[("active", UI.HEADER_DARK)])

            my_log = ttk.Treeview(self,
                                columns=("No.","Time", "Error"),
                                show="headings",
                                style="Custom.Treeview")
            my_log.heading("No.", text="No.")
            my_log.heading("Time", text="Time")
            my_log.heading("Error", text="Error")
            my_log.column("No.", width=50, anchor="center")
            my_log.column("Time", width=150, anchor="center")
            my_log.column("Error", width=200, anchor="center")

            my_log.tag_configure("odd", background="#f5f7fa")
            my_log.tag_configure("even", background=UI.FORM_BG)

            my_log.pack(fill="both", expand=True, padx=10, pady=10)
            self.my_log = my_log
            
    class AttendanceGraph(tk.Frame):
        def __init__(self, parent, rows=None, **kwargs):
            super().__init__(parent, bg=UI.FORM_BG, **kwargs)
            self._draw(rows or [])

        def _draw(self, rows):
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib.dates as mdates
            from datetime import datetime

            days, time_ins, time_outs = [], [], []
            for row in rows:
                try:
                    day = row[0]
                    ti = datetime.strptime(row[1], "%I:%M%p") if row[1] and row[1] != "—" else None
                    to = datetime.strptime(row[2], "%I:%M %p") if row[2] and row[2] != "—" else None
                    days.append(day)
                    time_ins.append(ti.hour + ti.minute / 60 if ti else None)
                    time_outs.append(to.hour + to.minute / 60 if to else None)
                except Exception:
                    continue

            fig, ax = plt.subplots(figsize=(7, 3.5), facecolor=UI.FORM_BG)
            ax.set_facecolor(UI.FORM_BG)

            x = list(range(len(days)))
            
            ti_vals = [v if v is not None else float("nan") for v in time_ins]
            to_vals = [v if v is not None else float("nan") for v in time_outs]

            ax.plot(x, ti_vals, color="#28a745", linewidth=1.5, marker="o",
                    markersize=6, label="Time In", zorder=3)
            ax.plot(x, to_vals, color="#dc3545", linewidth=1.5, marker="o",
                    markersize=3, label="Time Out", zorder=3)
            
            ax.fill_between(x, ti_vals, alpha=0.08, color="#28a745")
            ax.fill_between(x, to_vals, alpha=0.08, color="#dc3545")

            ax.set_xticks(x)
            ax.set_xticklabels(days, rotation=30, ha="right",
                            fontsize=9, fontfamily="Segoe UI", color="#000000")
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda val, _: f"{int(val):02d}:{int((val % 1) * 60):02d}")
            )
            ax.set_ylabel("Time", fontsize=10, color="#333333")
            ax.set_xlabel("Day", fontsize=10, color="#333333")
            ax.set_title("Attendance Time Log", fontsize=13, fontweight="bold",
                        color=UI.HEADER_COLOR, pad=12)
            ax.tick_params(colors="#555555")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#dddddd")
            ax.spines["bottom"].set_color("#dddddd")
            ax.grid(axis="y", linestyle="--", alpha=0.4, color="#cccccc")

            legend = ax.legend(frameon=True, fontsize=9, loc="upper right")
            legend.get_frame().set_facecolor(UI.FORM_BG)
            legend.get_frame().set_edgecolor("#dddddd")

            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=self)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            plt.close(fig)
            
    
if __name__ == "__main__":
        ui = UI()
        ui.main.mainloop()