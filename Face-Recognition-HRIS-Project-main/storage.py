import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "hris.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                department TEXT NOT NULL,
                role_position TEXT NOT NULL,
                contact_number TEXT NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                verified INTEGER NOT NULL,
                score REAL,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                success INTEGER NOT NULL,
                score REAL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def employee_exists(employee_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM employees WHERE employee_id = ? LIMIT 1", (employee_id,)
        ).fetchone()
    return row is not None


def add_employee(
    employee_id: str,
    full_name: str,
    department: str,
    role_position: str,
    contact_number: str,
    email: str,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO employees (
                employee_id, full_name, department, role_position, contact_number, email, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (employee_id, full_name, department, role_position, contact_number, email, now),
        )


def get_employee(employee_id: str) -> Optional[Dict[str, str]]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT employee_id, full_name, department, role_position, contact_number, email, created_at
            FROM employees WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def list_employees() -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT employee_id, full_name, department, role_position, contact_number, email, created_at
            FROM employees
            ORDER BY full_name COLLATE NOCASE ASC
            """
        ).fetchall()
    return rows


def update_employee(
    original_employee_id: str,
    new_employee_id: str,
    full_name: str,
    department: str,
    role_position: str,
    contact_number: str,
    email: str,
) -> Tuple[bool, str]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT employee_id FROM employees WHERE employee_id = ?",
            (original_employee_id,),
        ).fetchone()
        if existing is None:
            return False, "Employee not found."

        if original_employee_id != new_employee_id:
            duplicate = conn.execute(
                "SELECT employee_id FROM employees WHERE employee_id = ?",
                (new_employee_id,),
            ).fetchone()
            if duplicate is not None:
                return False, "New Employee ID already exists."

        conn.execute("BEGIN")
        conn.execute(
            """
            UPDATE employees
            SET employee_id = ?, full_name = ?, department = ?, role_position = ?, contact_number = ?, email = ?
            WHERE employee_id = ?
            """,
            (new_employee_id, full_name, department, role_position, contact_number, email, original_employee_id),
        )
        if original_employee_id != new_employee_id:
            conn.execute(
                "UPDATE attendance_logs SET employee_id = ? WHERE employee_id = ?",
                (new_employee_id, original_employee_id),
            )
            conn.execute(
                "UPDATE verification_logs SET employee_id = ? WHERE employee_id = ?",
                (new_employee_id, original_employee_id),
            )
        conn.commit()
    return True, "Employee updated successfully."


def delete_employee_hard(employee_id: str) -> Tuple[bool, str]:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT employee_id FROM employees WHERE employee_id = ?",
            (employee_id,),
        ).fetchone()
        if existing is None:
            return False, "Employee not found."

        conn.execute("BEGIN")
        conn.execute("DELETE FROM attendance_logs WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM verification_logs WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
        conn.commit()
    return True, "Employee and related records deleted."


def get_last_attendance_action(employee_id: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT action
            FROM attendance_logs
            WHERE employee_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (employee_id,),
        ).fetchone()
    return row["action"] if row else None


def can_log_action(employee_id: str, action: str) -> Tuple[bool, str]:
    action = action.upper().strip()
    if action not in {"TIME_IN", "TIME_OUT"}:
        return False, "Invalid attendance action."

    last_action = get_last_attendance_action(employee_id)
    if action == "TIME_IN" and last_action == "TIME_IN":
        return False, "Employee is already timed in."
    if action == "TIME_OUT" and last_action != "TIME_IN":
        return False, "Cannot time out before a valid time in."
    return True, "OK"


def log_attendance(employee_id: str, action: str, verified: bool, score: Optional[float]) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO attendance_logs (employee_id, action, timestamp, verified, score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (employee_id, action, now, 1 if verified else 0, score),
        )


def log_verification(employee_id: Optional[str], success: bool, score: Optional[float], message: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO verification_logs (employee_id, success, score, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (employee_id, 1 if success else 0, score, message, now),
        )


def get_recent_attendance(limit: int = 100) -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT a.id, a.employee_id, e.full_name, a.action, a.timestamp, a.verified, a.score
            FROM attendance_logs a
            LEFT JOIN employees e ON e.employee_id = a.employee_id
            ORDER BY a.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def get_employee_attendance(employee_id: str, limit: int = 200) -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, employee_id, action, timestamp, verified, score
            FROM attendance_logs
            WHERE employee_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (employee_id, limit),
        ).fetchall()
    return rows


def get_recent_verification_errors(limit: int = 100) -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, employee_id, success, score, message, timestamp
            FROM verification_logs
            WHERE success = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def get_recent_verifications(limit: int = 200) -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, employee_id, success, score, message, timestamp
            FROM verification_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return rows


def get_daily_summary() -> List[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                date(timestamp) AS day,
                SUM(CASE WHEN action = 'TIME_IN' THEN 1 ELSE 0 END) AS total_time_in,
                SUM(CASE WHEN action = 'TIME_OUT' THEN 1 ELSE 0 END) AS total_time_out,
                COUNT(*) AS total_actions
            FROM attendance_logs
            GROUP BY date(timestamp)
            ORDER BY day DESC
            """
        ).fetchall()
    return rows
