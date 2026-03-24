import tkinter as tk
from tkinter import ttk


class ModernStyles:
    HEADER_BG = "#010066"
    HEADER_FG = "#ffffff"
    ACCENT_COLOR = "#caab2f"
    ACCENT_HOVER = "#b89a28"
    CARD_BG = "#ffffff"
    FORM_BG = "#f5f6fa"
    BORDER_COLOR = "#d1d5db"
    TEXT_PRIMARY = "#1f2937"
    TEXT_SECONDARY = "#6b7280"
    SUCCESS_COLOR = "#10b981"
    DANGER_COLOR = "#ef4444"
    WARNING_COLOR = "#f59e0b"
    DISABLED_BG = "#e5e7eb"
    DISABLED_FG = "#9ca3af"

    FONT_PRIMARY = ("Segoe UI", 10)
    FONT_HEADER = ("Segoe UI", 18, "bold")
    FONT_SUBHEADER = ("Segoe UI", 14, "bold")
    FONT_BUTTON = ("Segoe UI", 10, "bold")
    FONT_LABEL = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)

    PAD_X = 20
    PAD_Y = 15
    CARD_PAD = 20
    CORNER_RADIUS = 12


class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, bg=None, fg=None, width=140, height=38, corner_radius=20, **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent.cget("bg"), highlightthickness=0, **kwargs)
        
        self.command = command
        self.corner_radius = corner_radius
        self.bg = bg or ModernStyles.ACCENT_COLOR
        self.fg = fg or "#ffffff"
        self.default_bg = self.bg
        self.hover_bg = self._darken_color(self.bg, 0.85)
        self.text = text
        
        self.bound = False
        
        self._draw()
        self._bind_events()
    
    def _darken_color(self, color, factor):
        color = color.lstrip("#")
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r, g, b = int(r * factor), int(g * factor), int(b * factor)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _lighten_color(self, color, factor=1.2):
        color = color.lstrip("#")
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _draw(self, bg=None):
        self.delete("all")
        bg = bg or self.default_bg
        
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        if w < 50:
            w = self.winfo_width() or 140
        if h < 20:
            h = self.winfo_height() or 38
        
        r = self.corner_radius
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg, outline="")
        self.create_arc(w-r*2, 0, w, r*2, start=0, extent=90, fill=bg, outline="")
        self.create_arc(0, h-r*2, r*2, h, start=180, extent=90, fill=bg, outline="")
        self.create_arc(w-r*2, h-r*2, w, h, start=270, extent=90, fill=bg, outline="")
        self.create_rectangle(r, 0, w-r, h, fill=bg, outline="")
        self.create_rectangle(0, r, w, h-r, fill=bg, outline="")
        
        self.create_text(w/2, h/2, text=self.text, fill=self.fg, font=ModernStyles.FONT_BUTTON)
    
    def _bind_events(self):
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bound = True
    
    def _on_enter(self, e):
        self._draw(bg=self.hover_bg)
    
    def _on_leave(self, e):
        self._draw(bg=self.default_bg)
    
    def _on_click(self, e):
        self._draw(bg=self._darken_color(self.default_bg, 0.75))
    
    def _on_release(self, e):
        self._draw(bg=self.hover_bg)
        if self.command:
            self.command()
    
    def config(self, **kwargs):
        if "state" in kwargs:
            if kwargs["state"] == "disabled":
                self.default_bg = ModernStyles.DISABLED_BG
                self.hover_bg = ModernStyles.DISABLED_BG
                self.fg = ModernStyles.DISABLED_FG
            else:
                self.default_bg = self.bg
                self.hover_bg = self._darken_color(self.bg, 0.85)
                self.fg = "#ffffff"
        if "text" in kwargs:
            self.text = kwargs["text"]
        self._draw()
    
    def configure(self, **kwargs):
        self.config(**kwargs)


class ModernButton(tk.Frame):
    def __init__(self, parent, text, command, bg=None, fg=None, width=140, height=38, corner_radius=8, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.command = command
        self.bg_color = bg or ModernStyles.ACCENT_COLOR
        self.fg_color = fg or "#ffffff"
        self.corner_radius = corner_radius
        self.default_bg = self.bg_color
        
        self.config(bg=parent.cget("bg"))
        
        inner_frame = tk.Frame(self, bg=self.bg_color, cursor="hand2")
        inner_frame.pack(fill="both", expand=True, padx=2, pady=2)
        
        label = tk.Label(inner_frame, text=text, bg=self.bg_color, fg=self.fg_color, font=ModernStyles.FONT_BUTTON)
        label.pack(expand=True)
        
        self._inner = inner_frame
        self._label = label
        
        self._bind_hover(inner_frame, label)
        
        inner_frame.bind("<Button-1>", lambda e: self._on_click())
        label.bind("<Button-1>", lambda e: self._on_click())
        inner_frame.bind("<ButtonRelease-1>", lambda e: self._on_release())
        label.bind("<ButtonRelease-1>", lambda e: self._on_release())
        
        for widget in [inner_frame, label]:
            widget.bind("<Enter>", lambda e: self._on_enter())
            widget.bind("<Leave>", lambda e: self._on_leave())
    
    def _darken_color(self, color, factor=0.85):
        color = color.lstrip("#")
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r, g, b = max(0, int(r * factor)), max(0, int(g * factor)), max(0, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _lighten_color(self, color, factor=1.15):
        color = color.lstrip("#")
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        r, g, b = min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _bind_hover(self, frame, label):
        pass
    
    def _on_enter(self):
        if self.cget("state") != "disabled":
            self._inner.config(bg=self._darken_color(self.bg_color, 0.85))
            self._label.config(bg=self._darken_color(self.bg_color, 0.85))
    
    def _on_leave(self):
        if self.cget("state") != "disabled":
            self._inner.config(bg=self.bg_color)
            self._label.config(bg=self.bg_color)
    
    def _on_click(self):
        if self.cget("state") != "disabled":
            self._inner.config(bg=self._darken_color(self.bg_color, 0.75))
            self._label.config(bg=self._darken_color(self.bg_color, 0.75))
    
    def _on_release(self):
        if self.cget("state") != "disabled":
            self._inner.config(bg=self.bg_color)
            self._label.config(bg=self.bg_color)
            if self.command:
                self.command()
    
    def config(self, **kwargs):
        if "state" in kwargs:
            if kwargs["state"] == "disabled":
                self._inner.config(bg=ModernStyles.DISABLED_BG)
                self._label.config(bg=ModernStyles.DISABLED_BG, fg=ModernStyles.DISABLED_FG)
            else:
                self._inner.config(bg=self.bg_color)
                self._label.config(bg=self.bg_color, fg=self.fg_color)
        if "text" in kwargs:
            self._label.config(text=kwargs["text"])
    
    def configure(self, **kwargs):
        self.config(**kwargs)
    
    def pack_forget(self):
        super().pack_forget()
    
    def pack(self, **kwargs):
        super().pack(**kwargs)
    
    def grid_forget(self):
        super().grid_forget()
    
    def grid(self, **kwargs):
        super().grid(**kwargs)


class PrimaryButton(ModernButton):
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, text, command, bg=ModernStyles.ACCENT_COLOR, fg="#ffffff", **kwargs)


class SecondaryButton(ModernButton):
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, text, command, bg=ModernStyles.HEADER_BG, fg="#ffffff", **kwargs)


class DangerButton(ModernButton):
    def __init__(self, parent, text, command, **kwargs):
        super().__init__(parent, text, command, bg=ModernStyles.DANGER_COLOR, fg="#ffffff", **kwargs)


class ModernCard(tk.Frame):
    def __init__(self, parent, bg=None, padx=20, pady=20, corner_radius=12, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.card_bg = bg or ModernStyles.CARD_BG
        self.corner_radius = corner_radius
        self.config(bg=parent.cget("bg") if hasattr(parent, 'cget') else ModernStyles.FORM_BG)
        
        inner = tk.Frame(self, bg=self.card_bg, relief="flat")
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        
        self.inner = inner
    
    def pack(self, **kwargs):
        super().pack(**kwargs)
    
    def grid(self, **kwargs):
        super().grid(**kwargs)


class ModernLabel(tk.Label):
    def __init__(self, parent, text="", **kwargs):
        kwargs.setdefault("bg", parent.cget("bg") if hasattr(parent, 'cget') else ModernStyles.FORM_BG)
        kwargs.setdefault("fg", ModernStyles.TEXT_PRIMARY)
        kwargs.setdefault("font", ModernStyles.FONT_LABEL)
        super().__init__(parent, text=text, **kwargs)


class ModernEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, width=25, **kwargs):
        super().__init__(parent)
        self.config(bg=parent.cget("bg") if hasattr(parent, 'cget') else ModernStyles.FORM_BG)
        
        self._entry = tk.Entry(
            self,
            textvariable=textvariable,
            width=width,
            font=ModernStyles.FONT_PRIMARY,
            bg=ModernStyles.CARD_BG,
            fg=ModernStyles.TEXT_PRIMARY,
            relief="flat",
            highlightthickness=1,
            highlightcolor=ModernStyles.ACCENT_COLOR,
            highlightbackground=ModernStyles.BORDER_COLOR,
            insertbackground=ModernStyles.HEADER_BG,
        )
        self._entry.pack(fill="x", padx=8, pady=6)
        
        self.entry = self._entry
    
    def get(self):
        return self._entry.get()
    
    def set(self, value):
        self._entry.delete(0, tk.END)
        self._entry.insert(0, value)


class HoverLabel(tk.Label):
    def __init__(self, parent, text="", command=None, **kwargs):
        kwargs.setdefault("cursor", "hand2" if command else "")
        super().__init__(parent, text=text, **kwargs)
        self.command = command
        
        if command:
            self.bind("<Enter>", self._on_enter)
            self.bind("<Leave>", self._on_leave)
            self.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, e):
        self.config(fg=ModernStyles.ACCENT_COLOR)
    
    def _on_leave(self, e):
        self.config(fg=ModernStyles.HEADER_BG)
    
    def _on_click(self, e):
        if self.command:
            self.command()


class ModernNavButton(tk.Frame):
    def __init__(self, parent, text, command=None, is_active=False, **kwargs):
        super().__init__(parent)
        self.command = command
        self.is_active = is_active
        self.config(bg=parent.cget("bg") if hasattr(parent, 'cget') else ModernStyles.FORM_BG)
        
        self._label = tk.Label(
            self,
            text=text,
            font=ModernStyles.FONT_BUTTON,
            bg=ModernStyles.ACCENT_COLOR if is_active else "transparent",
            fg="#ffffff" if is_active else ModernStyles.TEXT_PRIMARY,
            padx=16,
            pady=8,
            cursor="hand2" if command else "",
        )
        self._label.pack(fill="both", expand=True)
        
        if command:
            for widget in [self._label]:
                widget.bind("<Button-1>", lambda e: self._click())
                widget.bind("<Enter>", lambda e: self._on_enter())
                widget.bind("<Leave>", lambda e: self._on_leave())
    
    def _on_enter(self):
        if not self.is_active and self.command:
            self._label.config(bg=ModernStyles.ACCENT_COLOR + "40")
    
    def _on_leave(self):
        if not self.is_active:
            self._label.config(bg="transparent")
    
    def _click(self):
        if self.command:
            self.command()
    
    def set_active(self, active):
        self.is_active = active
        self._label.config(
            bg=ModernStyles.ACCENT_COLOR if active else "transparent",
            fg="#ffffff" if active else ModernStyles.TEXT_PRIMARY,
        )
    
    def config(self, **kwargs):
        if "state" in kwargs:
            if kwargs["state"] == "disabled":
                self._label.config(state="disabled", cursor="")
            else:
                self._label.config(state="normal", cursor="hand2")
        if "text" in kwargs:
            self._label.config(text=kwargs["text"])
    
    def configure(self, **kwargs):
        self.config(**kwargs)


def apply_modern_style():
    style = ttk.Style()
    style.theme_use('clam')
    
    style.configure("TFrame", background=ModernStyles.FORM_BG)
    style.configure("Card.TFrame", background=ModernStyles.CARD_BG, relief="flat")
    
    style.configure("TLabel", background=ModernStyles.FORM_BG, foreground=ModernStyles.TEXT_PRIMARY, font=ModernStyles.FONT_LABEL)
    style.configure("Header.TLabel", background=ModernStyles.HEADER_BG, foreground=ModernStyles.HEADER_FG, font=ModernStyles.FONT_HEADER)
    
    style.configure("TButton", 
                    background=ModernStyles.ACCENT_COLOR,
                    foreground="#ffffff",
                    font=ModernStyles.FONT_BUTTON,
                    padding=(12, 8),
                    relief="flat")
    
    style.map("TButton",
              background=[("active", ModernStyles.ACCENT_HOVER), ("disabled", ModernStyles.DISABLED_BG)],
              foreground=[("disabled", ModernStyles.DISABLED_FG)])
    
    style.configure("Treeview",
                    background=ModernStyles.CARD_BG,
                    foreground=ModernStyles.TEXT_PRIMARY,
                    fieldbackground=ModernStyles.CARD_BG,
                    font=ModernStyles.FONT_PRIMARY,
                    rowheight=28)
    
    style.configure("Treeview.Heading",
                    background=ModernStyles.HEADER_BG,
                    foreground=ModernStyles.HEADER_FG,
                    font=ModernStyles.FONT_BUTTON,
                    padding=(8, 6))
    
    style.map("Treeview",
              background=[("selected", ModernStyles.ACCENT_COLOR + "40")],
              foreground=[("selected", ModernStyles.TEXT_PRIMARY)])
    
    style.configure("TNotebook", background=ModernStyles.FORM_BG, relief="flat", borderwidth=0)
    style.configure("TNotebook.Tab", background=ModernStyles.CARD_BG, foreground=ModernStyles.TEXT_PRIMARY, padding=(16, 8), font=ModernStyles.FONT_BUTTON)
    style.map("TNotebook.Tab", background=[("selected", ModernStyles.ACCENT_COLOR)], foreground=[("selected", "#ffffff")])
    
    return style


def create_gradient_header(canvas, width, height, color1=ModernStyles.HEADER_BG, color2=None):
    if color2 is None:
        color2 = _lighten_hex(color1, 1.15)
    
    steps = 50
    for i in range(steps):
        ratio = i / steps
        color = _interpolate_color(color1, color2, ratio)
        y1 = int(height * i / steps)
        y2 = int(height * (i + 1) / steps)
        canvas.create_rectangle(0, y1, width, y2, fill=color, outline="")


def _lighten_hex(hex_color, factor=1.2):
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _interpolate_color(color1, color2, ratio):
    c1 = color1.lstrip("#")
    c2 = color2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    return f"#{r:02x}{g:02x}{b:02x}"


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.canvas = tk.Canvas(self, bg=ModernStyles.FORM_BG, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_frame = tk.Frame(self.canvas, bg=ModernStyles.FORM_BG)
        
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def pack(self, **kwargs):
        super().pack(**kwargs)
    
    def grid(self, **kwargs):
        super().grid(**kwargs)
