import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from face_service import (
	delete_employee_face_data,
	list_employee_photo_paths,
	rename_employee_face_folder,
)
from modern_ui import (
    ModernStyles,
    ModernButton,
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    ModernCard,
    create_gradient_header,
)
from storage import (
	delete_employee_hard,
	get_daily_summary,
	get_employee,
	get_employee_attendance,
	get_recent_attendance,
	get_recent_errors,
	get_recent_verifications,
	list_employees,
	update_attendance_log,
	update_employee,
	update_error_log,
	update_verification_log,
)

BG_COLOR = "#f0f2f5"
HEADER_COLOR = "#010066"
ACCENT_COLOR = "#caab2f"


class AdminPanel(tk.Toplevel):
	"""Admin portal for global employee management, log inspection, and log editing."""

	def __init__(self, parent, on_status=None, on_reenroll=None, current_manager_id=None):
		super().__init__(parent)
		self.title("Admin Panel - HRIS Management")
		self.geometry("1100x700")
		self.minsize(1000, 650)
		self.config(bg=BG_COLOR)

		self.on_status = on_status
		self.on_reenroll = on_reenroll
		self.current_manager_id = current_manager_id
		self.selected_employee_id = None
		self.preview_image = None

		self._build_ui()
		self.refresh_all()

	def _set_status(self, message):
		if callable(self.on_status):
			self.on_status(message)

	def _create_header(self):
		header = tk.Frame(self, bg=HEADER_COLOR)
		header.pack(fill="x")
		
		header_canvas = tk.Canvas(header, height=70, bg=HEADER_COLOR, highlightthickness=0)
		header_canvas.pack(fill="x")
		header_canvas.update_idletasks()
		
		w = header_canvas.winfo_width()
		if w < 100:
			w = 1100
		
		create_gradient_header(header_canvas, w, 70)
		
		header_canvas.create_text(w//2, 28, text="HRIS Admin Panel", fill="#ffffff", 
								  font=("Segoe UI", 20, "bold"), anchor="center")
		header_canvas.create_text(w//2, 52, text=f"Manager: {self.current_manager_id}", fill="#caab2f", 
								  font=("Segoe UI", 11), anchor="center")

	def _build_ui(self):
		self._create_header()
		
		root = tk.Frame(self, bg=BG_COLOR, padx=10, pady=10)
		root.pack(fill="both", expand=True)

		notebook_style = ttk.Style()
		notebook_style.configure("Modern.TNotebook", background=BG_COLOR, tabposition="n")
		notebook_style.configure("Modern.TNotebook.Tab", padding=(16, 8), font=("Segoe UI", 10, "bold"))
		
		notebook = ttk.Notebook(root, style="Modern.TNotebook")
		notebook.pack(fill="both", expand=True)

		tab_style = ttk.Style()
		tab_style.configure("Custom.TFrame", background=BG_COLOR)

		self.tab_employees = ttk.Frame(notebook, style="Custom.TFrame")
		self.tab_logs = ttk.Frame(notebook, style="Custom.TFrame")
		self.tab_summary = ttk.Frame(notebook, style="Custom.TFrame")

		notebook.add(self.tab_employees, text="  Employees  ")
		notebook.add(self.tab_logs, text="  Logs  ")
		notebook.add(self.tab_summary, text="  Summary  ")

		self._build_employees_tab()
		self._build_logs_tab()
		self._build_summary_tab()

	def _build_employees_tab(self):
		self.tab_employees.columnconfigure(0, weight=3)
		self.tab_employees.columnconfigure(1, weight=2)
		self.tab_employees.rowconfigure(1, weight=1)

		toolbar = tk.Frame(self.tab_employees, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 10))
		
		btn_refresh = ModernButton(toolbar, text="Refresh", command=self.refresh_employees, width=100)
		btn_refresh.pack(side="left", padx=(0, 8))
		
		btn_delete = DangerButton(toolbar, text="Delete Employee", command=self._delete_selected_employee, width=130)
		btn_delete.pack(side="left", padx=8)
		
		reenroll_state = "normal" if callable(self.on_reenroll) else "disabled"
		btn_reenroll = PrimaryButton(toolbar, text="Re-enroll Face", command=self._reenroll_selected_employee, width=120)
		btn_reenroll.pack(side="left")
		if not callable(self.on_reenroll):
			btn_reenroll.config(state="disabled")

		left = tk.Frame(self.tab_employees, bg=ModernStyles.CARD_BG)
		left.grid(row=1, column=0, sticky="nsew", padx=(6, 4), pady=(0, 6))

		cols = ("employee_id", "full_name", "department", "role_position")
		self.employee_tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
		self.employee_tree.heading("employee_id", text="Employee ID")
		self.employee_tree.heading("full_name", text="Full Name")
		self.employee_tree.heading("department", text="Department")
		self.employee_tree.heading("role_position", text="Role")
		self.employee_tree.column("employee_id", width=120, stretch=False)
		self.employee_tree.column("full_name", width=180)
		self.employee_tree.column("department", width=140)
		self.employee_tree.column("role_position", width=140)
		self.employee_tree.grid(row=0, column=0, sticky="nsew")
		self.employee_tree.bind("<<TreeviewSelect>>", self._on_employee_selected)

		yscroll = ttk.Scrollbar(left, orient="vertical", command=self.employee_tree.yview)
		self.employee_tree.configure(yscrollcommand=yscroll.set)
		yscroll.grid(row=0, column=1, sticky="ns")

		right = tk.Frame(self.tab_employees, bg=ModernStyles.CARD_BG)
		right.grid(row=1, column=1, sticky="nsew", padx=(4, 6), pady=(0, 6))
		right.columnconfigure(1, weight=1)
		right.rowconfigure(13, weight=1)

		self._entry_vars = {
			"employee_id": tk.StringVar(),
			"full_name": tk.StringVar(),
			"department": tk.StringVar(),
			"role_position": tk.StringVar(),
			"contact_number": tk.StringVar(),
			"email": tk.StringVar(),
			"manager_id": tk.StringVar(),
			"schedule_time_in": tk.StringVar(),
			"schedule_time_out": tk.StringVar(),
		}

		fields = [
			("Employee ID", "employee_id"),
			("Full Name", "full_name"),
			("Department", "department"),
			("Role", "role_position"),
			("Contact", "contact_number"),
			("Email", "email"),
			("Manager ID", "manager_id"),
			("Schedule Time In", "schedule_time_in"),
			("Schedule Time Out", "schedule_time_out"),
		]
		
		for row, (label, key) in enumerate(fields):
			tk.Label(right, text=label, bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
					font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", pady=3, padx=(10, 5))
			entry = tk.Entry(right, textvariable=self._entry_vars[key], font=("Segoe UI", 10),
							bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY, relief="flat")
			entry.grid(row=row, column=1, sticky="ew", pady=3, padx=(0, 10))

		btn_update = PrimaryButton(right, text="Update Employee", command=self._update_selected_employee, width=180)
		btn_update.grid(row=len(fields), column=0, columnspan=2, sticky="ew", pady=(12, 10), padx=10)

		tk.Label(right, text="Saved Photos", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 10, "bold")).grid(row=len(fields)+1, column=0, columnspan=2, sticky="w", padx=10)
		
		photo_frame = tk.Frame(right, bg=ModernStyles.CARD_BG)
		photo_frame.grid(row=len(fields)+2, column=0, columnspan=2, sticky="nsew")
		photo_frame.columnconfigure(0, weight=1)
		photo_frame.rowconfigure(0, weight=1)

		self.photo_list = tk.Listbox(photo_frame, height=8, font=("Segoe UI", 10),
									bg="#ffffff", fg=ModernStyles.TEXT_PRIMARY,
									relief="flat", selectbackground=ACCENT_COLOR, selectforeground="#ffffff")
		self.photo_list.grid(row=0, column=0, sticky="nsew")
		self.photo_list.bind("<<ListboxSelect>>", self._on_photo_selected)

		photo_scroll = ttk.Scrollbar(photo_frame, orient="vertical", command=self.photo_list.yview)
		self.photo_list.configure(yscrollcommand=photo_scroll.set)
		photo_scroll.grid(row=0, column=1, sticky="ns")

		self.photo_preview = tk.Label(right, text="No photo selected", anchor="center",
									 bg=ModernStyles.FORM_BG, fg=ModernStyles.TEXT_SECONDARY,
									 font=("Segoe UI", 9), relief="flat")
		self.photo_preview.grid(row=len(fields)+3, column=0, columnspan=2, sticky="nsew", pady=(8, 0), padx=10)

	def _build_logs_tab(self):
		self.tab_logs.rowconfigure(1, weight=1)
		self.tab_logs.columnconfigure(0, weight=1)

		toolbar = tk.Frame(self.tab_logs, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(0, 10))
		
		btn_refresh = ModernButton(toolbar, text="Refresh Logs", command=self.refresh_logs, width=120)
		btn_refresh.pack(side="left", padx=(0, 8))
		
		btn_verif = SecondaryButton(toolbar, text="Edit Verification", command=self._open_verification_editor, width=150)
		btn_verif.pack(side="left", padx=8)
		
		btn_error = SecondaryButton(toolbar, text="Edit Error Logs", command=self._open_error_editor, width=130)
		btn_error.pack(side="left", padx=8)
		
		btn_attend = SecondaryButton(toolbar, text="Edit Attendance", command=self._open_attendance_editor, width=140)
		btn_attend.pack(side="left")

		self.log_text = tk.Text(self.tab_logs, wrap="word", font=("Segoe UI", 10),
							   bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
							   relief="flat", padx=10, pady=10)
		self.log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
		self.log_text.config(state="disabled")

	def _build_summary_tab(self):
		self.tab_summary.rowconfigure(1, weight=1)
		self.tab_summary.columnconfigure(0, weight=1)

		toolbar = tk.Frame(self.tab_summary, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(0, 10))
		
		btn_refresh = ModernButton(toolbar, text="Refresh Summary", command=self.refresh_summary, width=140)
		btn_refresh.pack(side="left")

		self.summary_text = tk.Text(self.tab_summary, wrap="word", font=("Segoe UI", 10),
								   bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
								   relief="flat", padx=10, pady=10)
		self.summary_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
		self.summary_text.config(state="disabled")

	def refresh_all(self):
		self.refresh_employees()
		self.refresh_logs()
		self.refresh_summary()

	def refresh_employees(self):
		for item in self.employee_tree.get_children():
			self.employee_tree.delete(item)

		for row in list_employees(self.current_manager_id):
			self.employee_tree.insert(
				"",
				"end",
				iid=row["employee_id"],
				values=(row["employee_id"], row["full_name"], row["department"], row["role_position"]),
			)

		self.selected_employee_id = None
		self._clear_employee_form()
		self.photo_list.delete(0, "end")
		self.photo_preview.configure(text="No photo selected", image="")

	def refresh_logs(self):
		managed_ids = {row["employee_id"] for row in list_employees(self.current_manager_id)}
		
		verification_rows = get_recent_verifications(limit=300)
		if self.current_manager_id is not None:
			verification_rows = [r for r in verification_rows if r["employee_id"] in managed_ids]

		lines = ["Verification Logs", "-" * 85]
		for row in verification_rows:
			lines.append(
				f"[{row['timestamp']}] employee={row['employee_id'] or 'N/A'} | "
				f"success={bool(row['success'])} | score={row['score'] if row['score'] is not None else 'N/A'} | "
				f"{row['message']}"
			)

		error_rows = get_recent_errors(limit=300)
		if self.current_manager_id is not None:
			error_rows = [r for r in error_rows if r["employee_id"] in managed_ids]
			
		lines.append("\n" + "Error Logs" + "\n" + "-" * 85)
		for row in error_rows:
			lines.append(
				f"[{row['timestamp']}] employee={row['employee_id'] or 'N/A'} | "
				f"score={row['score'] if row['score'] is not None else 'N/A'} | "
				f"{row['message']}"
			)

		lines.append("\n" + "Attendance Logs" + "\n" + "-" * 85)
		for emp in list_employees(self.current_manager_id):
			emp_logs = get_employee_attendance(emp["employee_id"], limit=20)
			if not emp_logs:
				continue
			lines.append(f"\n{emp['employee_id']} - {emp['full_name']}")
			for log in emp_logs[:6]:
				lines.append(
					f"  [{log['timestamp']}] {log['action']} | verified={bool(log['verified'])} | "
					f"score={log['score'] if log['score'] is not None else 'N/A'}"
				)

		self.log_text.config(state="normal")
		self.log_text.delete("1.0", "end")
		self.log_text.insert("1.0", "\n".join(lines) if lines else "No logs found.")
		self.log_text.config(state="disabled")

	def refresh_summary(self):
		rows = get_daily_summary(self.current_manager_id)
		lines = ["Daily Attendance Summary", "-" * 80]
		for row in rows:
			lines.append(
				f"{row['day']}: Time In={row['total_time_in']} | Time Out={row['total_time_out']} | Total={row['total_actions']}"
			)

		self.summary_text.config(state="normal")
		self.summary_text.delete("1.0", "end")
		self.summary_text.insert("1.0", "\n".join(lines) if lines else "No summary data found.")
		self.summary_text.config(state="disabled")

	def _clear_employee_form(self):
		for var in self._entry_vars.values():
			var.set("")

	def _on_employee_selected(self, _event):
		selected = self.employee_tree.selection()
		if not selected:
			return

		employee_id = selected[0]
		self.selected_employee_id = employee_id
		employee = get_employee(employee_id)
		if employee is None:
			return

		for key in self._entry_vars:
			self._entry_vars[key].set(employee.get(key, ""))

		self.photo_list.delete(0, "end")
		self._photo_paths = list_employee_photo_paths(employee_id)
		for path in self._photo_paths:
			self.photo_list.insert("end", path.name)
		self.photo_preview.configure(text="No photo selected", image="")

	def _on_photo_selected(self, _event):
		if not hasattr(self, "_photo_paths"):
			return
		idxs = self.photo_list.curselection()
		if not idxs:
			return
		path = self._photo_paths[idxs[0]]
		if not path.exists():
			return

		image = Image.open(path)
		image = image.resize((180, 180), Image.Resampling.LANCZOS)
		self.preview_image = ImageTk.PhotoImage(image)
		self.photo_preview.configure(image=self.preview_image, text="")

	def _update_selected_employee(self):
		if not self.selected_employee_id:
			messagebox.showwarning("Admin", "Select an employee first.")
			return

		payload = {key: var.get().strip() for key, var in self._entry_vars.items()}
		if not all(payload.values()):
			messagebox.showwarning("Admin", "All profile fields are required.")
			return

		if self.selected_employee_id == self.current_manager_id:
			messagebox.showwarning("Admin", "You cannot edit your own profile.")
			return

		ok, msg = update_employee(
			self.selected_employee_id,
			payload["employee_id"],
			payload["full_name"],
			payload["department"],
			payload["role_position"],
			payload["contact_number"],
			payload["email"],
			payload.get("manager_id") or None,
			payload.get("schedule_time_in") or "09:00",
			payload.get("schedule_time_out") or "17:00",
		)
		if not ok:
			messagebox.showerror("Admin", msg)
			return

		rename_employee_face_folder(self.selected_employee_id, payload["employee_id"])
		self.selected_employee_id = payload["employee_id"]
		self.refresh_all()
		self._set_status(f"Admin updated employee: {payload['employee_id']}")

	def _delete_selected_employee(self):
		if not self.selected_employee_id:
			messagebox.showwarning("Admin", "Select an employee first.")
			return

		confirmed = messagebox.askyesno(
			"Confirm Hard Delete",
			"Delete employee, photos, attendance logs, and verification logs permanently?",
		)
		if not confirmed:
			return

		emp_id = self.selected_employee_id
		ok, msg = delete_employee_hard(emp_id)
		if not ok:
			messagebox.showerror("Admin", msg)
			return

		delete_employee_face_data(emp_id)
		self.refresh_all()
		self._set_status(f"Admin deleted employee: {emp_id}")

	def _reenroll_selected_employee(self):
		if not self.selected_employee_id:
			messagebox.showwarning("Admin", "Select an employee first.")
			return
		if not callable(self.on_reenroll):
			messagebox.showerror("Admin", "Re-enroll callback is not available.")
			return

		self.on_reenroll(self.selected_employee_id)
		self._set_status(f"Re-enrollment started for {self.selected_employee_id}. Please return to main window camera.")

	def _open_verification_editor(self):
		editor = tk.Toplevel(self)
		editor.title("Edit Verification Logs")
		editor.geometry("980x560")
		editor.config(bg=BG_COLOR)

		root = tk.Frame(editor, bg=BG_COLOR, padx=10, pady=10)
		root.pack(fill="both", expand=True)
		root.columnconfigure(0, weight=1)
		root.rowconfigure(1, weight=1)

		toolbar = tk.Frame(root, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
		
		btn_reload = ModernButton(toolbar, text="Reload", command=lambda: load_rows(), width=100)
		btn_reload.pack(side="left", padx=(0, 8))
		
		btn_save = PrimaryButton(toolbar, text="Save Edit", command=save, width=100)
		btn_save.pack(side="left")

		cols = ("id", "timestamp", "employee_id", "success", "score", "message")
		tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
		for col in cols:
			tree.heading(col, text=col.replace("_", " ").title())
		tree.column("id", width=70, stretch=False)
		tree.column("timestamp", width=180, stretch=False)
		tree.column("employee_id", width=120, stretch=False)
		tree.column("success", width=80, stretch=False)
		tree.column("score", width=90, stretch=False)
		tree.column("message", width=360)
		tree.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

		form = tk.Frame(root, bg=ModernStyles.CARD_BG)
		form.grid(row=2, column=0, sticky="ew", pady=(0, 0))
		form.columnconfigure(1, weight=1)

		employee_var = tk.StringVar()
		success_var = tk.StringVar()
		score_var = tk.StringVar()
		message_var = tk.StringVar()
		timestamp_var = tk.StringVar()

		row = 0
		tk.Label(form, text="Employee ID", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=employee_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
		tk.Label(form, text="Success (0/1)", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=success_var, width=8, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=3, sticky="w", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Score", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=score_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
		tk.Label(form, text="Timestamp (ISO)", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=timestamp_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=3, sticky="ew", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Message", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=message_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, columnspan=3, sticky="ew", padx=4, pady=2)

		state = {"selected_id": None}

		def load_rows():
			for item in tree.get_children():
				tree.delete(item)
			for row_data in get_recent_verifications(limit=500):
				tree.insert(
					"",
					"end",
					iid=str(row_data["id"]),
					values=(
						row_data["id"],
						row_data["timestamp"],
						row_data["employee_id"] or "",
						row_data["success"],
						"" if row_data["score"] is None else row_data["score"],
						row_data["message"],
					),
				)

		def on_select(_event):
			selected = tree.selection()
			if not selected:
				return
			item = tree.item(selected[0])
			values = item["values"]
			state["selected_id"] = int(values[0])
			timestamp_var.set(str(values[1]))
			employee_var.set(str(values[2]))
			success_var.set(str(values[3]))
			score_var.set(str(values[4]))
			message_var.set(str(values[5]))

		def save():
			if state["selected_id"] is None:
				messagebox.showwarning("Admin", "Select a verification log first.")
				return

			success_text = success_var.get().strip()
			if success_text not in {"0", "1"}:
				messagebox.showerror("Admin", "Success must be 0 or 1.")
				return

			score_text = score_var.get().strip()
			if score_text == "":
				score_value = None
			else:
				try:
					score_value = float(score_text)
				except ValueError:
					messagebox.showerror("Admin", "Score must be a number.")
					return

			ok, msg = update_verification_log(
				state["selected_id"],
				employee_var.get().strip() or None,
				success_text == "1",
				score_value,
				message_var.get().strip(),
				timestamp_var.get().strip(),
			)
			if not ok:
				messagebox.showerror("Admin", msg)
				return

			self.refresh_logs()
			load_rows()
			self._set_status("Verification log updated.")

		tree.bind("<<TreeviewSelect>>", on_select)
		load_rows()

	def _open_attendance_editor(self):
		editor = tk.Toplevel(self)
		editor.title("Edit Attendance Logs")
		editor.geometry("980x560")
		editor.config(bg=BG_COLOR)

		root = tk.Frame(editor, bg=BG_COLOR, padx=10, pady=10)
		root.pack(fill="both", expand=True)
		root.columnconfigure(0, weight=1)
		root.rowconfigure(1, weight=1)

		toolbar = tk.Frame(root, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
		
		btn_reload = ModernButton(toolbar, text="Reload", command=lambda: load_rows(), width=100)
		btn_reload.pack(side="left", padx=(0, 8))
		
		btn_save = PrimaryButton(toolbar, text="Save Edit", command=save, width=100)
		btn_save.pack(side="left")

		cols = ("id", "timestamp", "employee_id", "action", "verified", "score")
		tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
		for col in cols:
			tree.heading(col, text=col.replace("_", " ").title())
		tree.column("id", width=70, stretch=False)
		tree.column("timestamp", width=180, stretch=False)
		tree.column("employee_id", width=120, stretch=False)
		tree.column("action", width=100, stretch=False)
		tree.column("verified", width=80, stretch=False)
		tree.column("score", width=90, stretch=False)
		tree.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

		form = tk.Frame(root, bg=ModernStyles.CARD_BG)
		form.grid(row=2, column=0, sticky="ew", pady=(0, 0))
		form.columnconfigure(1, weight=1)

		employee_var = tk.StringVar()
		action_var = tk.StringVar()
		verified_var = tk.StringVar()
		score_var = tk.StringVar()
		timestamp_var = tk.StringVar()

		row = 0
		tk.Label(form, text="Employee ID", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=employee_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
		tk.Label(form, text="Action", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=4, pady=2)
		ttk.Combobox(form, textvariable=action_var, values=["TIME_IN", "TIME_OUT"], state="readonly",
				   font=("Segoe UI", 10)).grid(row=row, column=3, sticky="ew", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Verified (0/1)", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=verified_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
		tk.Label(form, text="Score", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=score_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=3, sticky="ew", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Timestamp (ISO)", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=timestamp_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, columnspan=3, sticky="ew", padx=4, pady=2)

		state = {"selected_id": None}

		def load_rows():
			for item in tree.get_children():
				tree.delete(item)
			for row_data in get_recent_attendance(limit=500):
				tree.insert(
					"",
					"end",
					iid=str(row_data["id"]),
					values=(
						row_data["id"],
						row_data["timestamp"],
						row_data["employee_id"],
						row_data["action"],
						row_data["verified"],
						"" if row_data["score"] is None else row_data["score"],
					),
				)

		def on_select(_event):
			selected = tree.selection()
			if not selected:
				return
			item = tree.item(selected[0])
			values = item["values"]
			state["selected_id"] = int(values[0])
			timestamp_var.set(str(values[1]))
			employee_var.set(str(values[2]))
			action_var.set(str(values[3]))
			verified_var.set(str(values[4]))
			score_var.set(str(values[5]))

		def save():
			if state["selected_id"] is None:
				messagebox.showwarning("Admin", "Select an attendance log first.")
				return

			verified_text = verified_var.get().strip()
			if verified_text not in {"0", "1"}:
				messagebox.showerror("Admin", "Verified must be 0 or 1.")
				return

			score_text = score_var.get().strip()
			if score_text == "":
				score_value = None
			else:
				try:
					score_value = float(score_text)
				except ValueError:
					messagebox.showerror("Admin", "Score must be a number.")
					return

			ok, msg = update_attendance_log(
				state["selected_id"],
				employee_var.get().strip(),
				action_var.get().strip(),
				verified_text == "1",
				score_value,
				timestamp_var.get().strip(),
			)
			if not ok:
				messagebox.showerror("Admin", msg)
				return

			self.refresh_logs()
			load_rows()
			self._set_status("Attendance log updated.")

		tree.bind("<<TreeviewSelect>>", on_select)
		load_rows()

	def _open_error_editor(self):
		editor = tk.Toplevel(self)
		editor.title("Edit Error Logs")
		editor.geometry("980x560")
		editor.config(bg=BG_COLOR)

		root = tk.Frame(editor, bg=BG_COLOR, padx=10, pady=10)
		root.pack(fill="both", expand=True)
		root.columnconfigure(0, weight=1)
		root.rowconfigure(1, weight=1)

		toolbar = tk.Frame(root, bg=BG_COLOR)
		toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
		
		btn_reload = ModernButton(toolbar, text="Reload", command=lambda: load_rows(), width=100)
		btn_reload.pack(side="left", padx=(0, 8))
		
		btn_save = PrimaryButton(toolbar, text="Save Edit", command=save, width=100)
		btn_save.pack(side="left")

		cols = ("id", "timestamp", "employee_id", "score", "message")
		tree = ttk.Treeview(root, columns=cols, show="headings", selectmode="browse")
		for col in cols:
			tree.heading(col, text=col.replace("_", " ").title())
		tree.column("id", width=70, stretch=False)
		tree.column("timestamp", width=180, stretch=False)
		tree.column("employee_id", width=120, stretch=False)
		tree.column("score", width=90, stretch=False)
		tree.column("message", width=420)
		tree.grid(row=1, column=0, sticky="nsew", pady=(0, 10))

		form = tk.Frame(root, bg=ModernStyles.CARD_BG)
		form.grid(row=2, column=0, sticky="ew", pady=(0, 0))
		form.columnconfigure(1, weight=1)

		employee_var = tk.StringVar()
		score_var = tk.StringVar()
		message_var = tk.StringVar()
		timestamp_var = tk.StringVar()

		row = 0
		tk.Label(form, text="Employee ID", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=employee_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, sticky="ew", padx=4, pady=2)
		tk.Label(form, text="Score", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=2, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=score_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=3, sticky="ew", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Timestamp (ISO)", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=timestamp_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, columnspan=3, sticky="ew", padx=4, pady=2)

		row += 1
		tk.Label(form, text="Message", bg=ModernStyles.CARD_BG, fg=ModernStyles.TEXT_PRIMARY,
				font=("Segoe UI", 9)).grid(row=row, column=0, sticky="w", padx=4, pady=2)
		tk.Entry(form, textvariable=message_var, font=("Segoe UI", 10), bg="#ffffff",
				fg=ModernStyles.TEXT_PRIMARY, relief="flat").grid(row=row, column=1, columnspan=3, sticky="ew", padx=4, pady=2)

		state = {"selected_id": None}

		def load_rows():
			for item in tree.get_children():
				tree.delete(item)
			for row_data in get_recent_errors(limit=500):
				tree.insert(
					"",
					"end",
					iid=str(row_data["id"]),
					values=(
						row_data["id"],
						row_data["timestamp"],
						row_data["employee_id"] or "",
						"" if row_data["score"] is None else row_data["score"],
						row_data["message"],
					),
				)

		def on_select(_event):
			selected = tree.selection()
			if not selected:
				return
			item = tree.item(selected[0])
			values = item["values"]
			state["selected_id"] = int(values[0])
			timestamp_var.set(str(values[1]))
			employee_var.set(str(values[2]))
			score_var.set(str(values[3]))
			message_var.set(str(values[4]))

		def save():
			if state["selected_id"] is None:
				messagebox.showwarning("Admin", "Select an error log first.")
				return

			score_text = score_var.get().strip()
			if score_text == "":
				score_value = None
			else:
				try:
					score_value = float(score_text)
				except ValueError:
					messagebox.showerror("Admin", "Score must be a number.")
					return

			ok, msg = update_error_log(
				state["selected_id"],
				employee_var.get().strip() or None,
				score_value,
				message_var.get().strip(),
				timestamp_var.get().strip(),
			)
			if not ok:
				messagebox.showerror("Admin", msg)
				return

			self.refresh_logs()
			load_rows()
			self._set_status("Error log updated.")

		tree.bind("<<TreeviewSelect>>", on_select)
		load_rows()
