import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from face_service import (
	delete_employee_face_data,
	list_employee_photo_paths,
	rename_employee_face_folder,
)
from storage import (
	delete_employee_hard,
	get_daily_summary,
	get_employee,
	get_employee_attendance,
	get_recent_verifications,
	list_employees,
	update_employee,
)


class AdminPanel(tk.Toplevel):
	def __init__(self, parent, on_status=None, on_reenroll=None):
		super().__init__(parent)
		self.title("Admin Panel")
		self.geometry("1100x700")
		self.minsize(1000, 650)

		self.on_status = on_status
		self.on_reenroll = on_reenroll
		self.selected_employee_id = None
		self.preview_image = None

		self._build_ui()
		self.refresh_all()

	def _set_status(self, message):
		if callable(self.on_status):
			self.on_status(message)

	def _build_ui(self):
		root = ttk.Frame(self, padding=8)
		root.pack(fill="both", expand=True)

		notebook = ttk.Notebook(root)
		notebook.pack(fill="both", expand=True)

		self.tab_employees = ttk.Frame(notebook)
		self.tab_logs = ttk.Frame(notebook)
		self.tab_summary = ttk.Frame(notebook)

		notebook.add(self.tab_employees, text="Employees")
		notebook.add(self.tab_logs, text="Logs")
		notebook.add(self.tab_summary, text="Summary")

		self._build_employees_tab()
		self._build_logs_tab()
		self._build_summary_tab()

	def _build_employees_tab(self):
		self.tab_employees.columnconfigure(0, weight=3)
		self.tab_employees.columnconfigure(1, weight=2)
		self.tab_employees.rowconfigure(1, weight=1)

		toolbar = ttk.Frame(self.tab_employees)
		toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=6, pady=6)
		ttk.Button(toolbar, text="Refresh", command=self.refresh_employees).pack(side="left")
		ttk.Button(toolbar, text="Delete Employee", command=self._delete_selected_employee).pack(side="left", padx=6)
		ttk.Button(toolbar, text="Re-enroll Face", command=self._reenroll_selected_employee).pack(side="left")

		left = ttk.Frame(self.tab_employees)
		left.grid(row=1, column=0, sticky="nsew", padx=(6, 4), pady=(0, 6))
		left.rowconfigure(0, weight=1)
		left.columnconfigure(0, weight=1)

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

		right = ttk.Frame(self.tab_employees)
		right.grid(row=1, column=1, sticky="nsew", padx=(4, 6), pady=(0, 6))
		right.columnconfigure(1, weight=1)
		right.rowconfigure(9, weight=1)

		self._entry_vars = {
			"employee_id": tk.StringVar(),
			"full_name": tk.StringVar(),
			"department": tk.StringVar(),
			"role_position": tk.StringVar(),
			"contact_number": tk.StringVar(),
			"email": tk.StringVar(),
		}

		fields = [
			("Employee ID", "employee_id"),
			("Full Name", "full_name"),
			("Department", "department"),
			("Role", "role_position"),
			("Contact", "contact_number"),
			("Email", "email"),
		]
		for row, (label, key) in enumerate(fields):
			ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", pady=3)
			ttk.Entry(right, textvariable=self._entry_vars[key]).grid(row=row, column=1, sticky="ew", pady=3)

		ttk.Button(right, text="Update Employee", command=self._update_selected_employee).grid(
			row=6, column=0, columnspan=2, sticky="ew", pady=(6, 10)
		)

		ttk.Label(right, text="Saved Photos").grid(row=7, column=0, columnspan=2, sticky="w")
		photo_frame = ttk.Frame(right)
		photo_frame.grid(row=8, column=0, columnspan=2, sticky="nsew")
		photo_frame.columnconfigure(0, weight=1)
		photo_frame.rowconfigure(0, weight=1)

		self.photo_list = tk.Listbox(photo_frame, height=8)
		self.photo_list.grid(row=0, column=0, sticky="nsew")
		self.photo_list.bind("<<ListboxSelect>>", self._on_photo_selected)

		photo_scroll = ttk.Scrollbar(photo_frame, orient="vertical", command=self.photo_list.yview)
		self.photo_list.configure(yscrollcommand=photo_scroll.set)
		photo_scroll.grid(row=0, column=1, sticky="ns")

		self.photo_preview = ttk.Label(right, text="No photo selected", anchor="center")
		self.photo_preview.grid(row=9, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

	def _build_logs_tab(self):
		self.tab_logs.rowconfigure(1, weight=1)
		self.tab_logs.columnconfigure(0, weight=1)

		toolbar = ttk.Frame(self.tab_logs)
		toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
		ttk.Button(toolbar, text="Refresh Logs", command=self.refresh_logs).pack(side="left")

		self.log_text = tk.Text(self.tab_logs, wrap="word")
		self.log_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
		self.log_text.config(state="disabled")

	def _build_summary_tab(self):
		self.tab_summary.rowconfigure(1, weight=1)
		self.tab_summary.columnconfigure(0, weight=1)

		toolbar = ttk.Frame(self.tab_summary)
		toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
		ttk.Button(toolbar, text="Refresh Summary", command=self.refresh_summary).pack(side="left")

		self.summary_text = tk.Text(self.tab_summary, wrap="word")
		self.summary_text.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
		self.summary_text.config(state="disabled")

	def refresh_all(self):
		self.refresh_employees()
		self.refresh_logs()
		self.refresh_summary()

	def refresh_employees(self):
		for item in self.employee_tree.get_children():
			self.employee_tree.delete(item)

		for row in list_employees():
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
		verification_rows = get_recent_verifications(limit=300)
		lines = ["Verification Logs", "-" * 85]
		for row in verification_rows:
			lines.append(
				f"[{row['timestamp']}] employee={row['employee_id'] or 'N/A'} | "
				f"success={bool(row['success'])} | score={row['score'] if row['score'] is not None else 'N/A'} | "
				f"{row['message']}"
			)

		lines.append("\n" + "Attendance Logs" + "\n" + "-" * 85)
		for emp in list_employees():
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
		rows = get_daily_summary()
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

		ok, msg = update_employee(
			self.selected_employee_id,
			payload["employee_id"],
			payload["full_name"],
			payload["department"],
			payload["role_position"],
			payload["contact_number"],
			payload["email"],
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
