import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "hris.db"

# Storage backend selection:
# - sqlite   : local only
# - supabase : shared cloud database via Supabase REST API
STORAGE_BACKEND = os.getenv("HRIS_STORAGE_BACKEND", "sqlite").strip().lower()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


def _using_supabase() -> bool:
    return STORAGE_BACKEND == "supabase" and bool(SUPABASE_URL and SUPABASE_KEY)


def _supabase_headers(return_representation: bool = False) -> Dict[str, str]:
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if return_representation:
        headers["Prefer"] = "return=representation"
    return headers


def _supabase_request(
    method: str,
    table: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    payload: Optional[Any] = None,
    return_representation: bool = False,
) -> Any:
    if not _using_supabase():
        raise RuntimeError("Supabase backend is not configured.")

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    response = requests.request(
        method=method,
        url=url,
        headers=_supabase_headers(return_representation=return_representation),
        params=params,
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    if not response.text:
        return None
    return response.json()


def _to_row_list(items: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return items if items is not None else []


def _parse_iso_or_none(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    if _using_supabase():
        # Cloud mode expects schema pre-created in Supabase.
        return

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
                created_at TEXT NOT NULL,
                manager_id TEXT DEFAULT NULL,
                schedule_time_in TEXT DEFAULT '09:00',
                schedule_time_out TEXT DEFAULT '17:00',
                is_admin INTEGER DEFAULT 0,
                password_hash TEXT DEFAULT NULL
            )
            """
        )
        try:
            conn.execute("ALTER TABLE employees ADD COLUMN manager_id TEXT DEFAULT NULL")
            conn.execute("ALTER TABLE employees ADD COLUMN schedule_time_in TEXT DEFAULT '09:00'")
            conn.execute("ALTER TABLE employees ADD COLUMN schedule_time_out TEXT DEFAULT '17:00'")
            conn.execute("ALTER TABLE employees ADD COLUMN is_admin INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE employees ADD COLUMN password_hash TEXT DEFAULT NULL")
        except sqlite3.OperationalError:
            pass

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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                score REAL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )


def employee_exists(employee_id: str) -> bool:
    if _using_supabase():
        rows = _supabase_request(
            "GET",
            "employees",
            params={"select": "employee_id", "employee_id": f"eq.{employee_id}", "limit": 1},
        )
        return len(rows) > 0

    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM employees WHERE employee_id = ? LIMIT 1", (employee_id,)).fetchone()
    return row is not None


def add_employee(
    employee_id: str,
    full_name: str,
    department: str,
    role_position: str,
    contact_number: str,
    email: str,
    manager_id: Optional[str] = None,
    schedule_time_in: str = "09:00",
    schedule_time_out: str = "17:00",
    is_admin: int = 0,
    password_hash: Optional[str] = None,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    if _using_supabase():
        _supabase_request(
            "POST",
            "employees",
            payload={
                "employee_id": employee_id,
                "full_name": full_name,
                "department": department,
                "role_position": role_position,
                "contact_number": contact_number,
                "email": email,
                "created_at": now,
                "manager_id": manager_id,
                "schedule_time_in": schedule_time_in,
                "schedule_time_out": schedule_time_out,
                "is_admin": is_admin,
                "password_hash": password_hash,
            },
        )
        return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO employees (
                employee_id, full_name, department, role_position, contact_number, email, created_at,
                manager_id, schedule_time_in, schedule_time_out, is_admin, password_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (employee_id, full_name, department, role_position, contact_number, email, now, manager_id, schedule_time_in, schedule_time_out, is_admin, password_hash),
        )


def get_employee(employee_id: str) -> Optional[Dict[str, str]]:
    if _using_supabase():
        rows = _to_row_list(
            _supabase_request(
                "GET",
                "employees",
                params={
                    "select": "employee_id,full_name,department,role_position,contact_number,email,created_at,manager_id,schedule_time_in,schedule_time_out,is_admin,password_hash",
                    "employee_id": f"eq.{employee_id}",
                    "limit": 1,
                },
            )
        )
        return rows[0] if rows else None

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT employee_id, full_name, department, role_position, contact_number, email, created_at,
                   manager_id, schedule_time_in, schedule_time_out, is_admin, password_hash
            FROM employees WHERE employee_id = ?
            """,
            (employee_id,),
        ).fetchone()
    return dict(row) if row is not None else None


def list_employees(manager_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if _using_supabase():
        params = {
            "select": "employee_id,full_name,department,role_position,contact_number,email,created_at,manager_id,schedule_time_in,schedule_time_out,is_admin",
            "order": "full_name.asc",
        }
        if manager_id is not None:
            # We want to show employees directly assigned to this manager, 
            # OR employees who have NO manager assigned yet so the manager can adopt/assign them.
            params["or"] = f"(manager_id.eq.{manager_id},manager_id.is.null)"
            
        return _to_row_list(
            _supabase_request(
                "GET",
                "employees",
                params=params,
            )
        )

    with get_connection() as conn:
        if manager_id is not None:
            rows = conn.execute(
                """
                SELECT employee_id, full_name, department, role_position, contact_number, email, created_at,
                       manager_id, schedule_time_in, schedule_time_out, is_admin
                FROM employees
                WHERE manager_id = ? OR manager_id IS NULL OR manager_id = ''
                ORDER BY full_name COLLATE NOCASE ASC
                """,
                (manager_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT employee_id, full_name, department, role_position, contact_number, email, created_at,
                       manager_id, schedule_time_in, schedule_time_out, is_admin
                FROM employees
                ORDER BY full_name COLLATE NOCASE ASC
                """
            ).fetchall()
    return [dict(row) for row in rows]


def update_employee(
    original_employee_id: str,
    new_employee_id: str,
    full_name: str,
    department: str,
    role_position: str,
    contact_number: str,
    email: str,
    manager_id: Optional[str] = None,
    schedule_time_in: str = "09:00",
    schedule_time_out: str = "17:00",
) -> Tuple[bool, str]:
    if _using_supabase():
        existing = get_employee(original_employee_id)
        if existing is None:
            return False, "Employee not found."

        if original_employee_id != new_employee_id and employee_exists(new_employee_id):
            return False, "New Employee ID already exists."

        _supabase_request(
            "PATCH",
            "employees",
            params={"employee_id": f"eq.{original_employee_id}"},
            payload={
                "employee_id": new_employee_id,
                "full_name": full_name,
                "department": department,
                "role_position": role_position,
                "contact_number": contact_number,
                "email": email,
                "manager_id": manager_id,
                "schedule_time_in": schedule_time_in,
                "schedule_time_out": schedule_time_out,
            },
        )

        if original_employee_id != new_employee_id:
            _supabase_request(
                "PATCH",
                "attendance_logs",
                params={"employee_id": f"eq.{original_employee_id}"},
                payload={"employee_id": new_employee_id},
            )
            _supabase_request(
                "PATCH",
                "verification_logs",
                params={"employee_id": f"eq.{original_employee_id}"},
                payload={"employee_id": new_employee_id},
            )
            _supabase_request(
                "PATCH",
                "error_logs",
                params={"employee_id": f"eq.{original_employee_id}"},
                payload={"employee_id": new_employee_id},
            )
        return True, "Employee updated successfully."

    with get_connection() as conn:
        existing = conn.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (original_employee_id,)).fetchone()
        if existing is None:
            return False, "Employee not found."

        if original_employee_id != new_employee_id:
            duplicate = conn.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (new_employee_id,)).fetchone()
            if duplicate is not None:
                return False, "New Employee ID already exists."

        conn.execute("BEGIN")
        conn.execute(
            """
            UPDATE employees
            SET employee_id = ?, full_name = ?, department = ?, role_position = ?, contact_number = ?, email = ?,
                manager_id = ?, schedule_time_in = ?, schedule_time_out = ?
            WHERE employee_id = ?
            """,
            (new_employee_id, full_name, department, role_position, contact_number, email, manager_id, schedule_time_in, schedule_time_out, original_employee_id),
        )
        if original_employee_id != new_employee_id:
            conn.execute("UPDATE attendance_logs SET employee_id = ? WHERE employee_id = ?", (new_employee_id, original_employee_id))
            conn.execute("UPDATE verification_logs SET employee_id = ? WHERE employee_id = ?", (new_employee_id, original_employee_id))
            conn.execute("UPDATE error_logs SET employee_id = ? WHERE employee_id = ?", (new_employee_id, original_employee_id))
        conn.commit()
    return True, "Employee updated successfully."


def delete_employee_hard(employee_id: str) -> Tuple[bool, str]:
    if _using_supabase():
        if not employee_exists(employee_id):
            return False, "Employee not found."

        _supabase_request("DELETE", "attendance_logs", params={"employee_id": f"eq.{employee_id}"})
        _supabase_request("DELETE", "verification_logs", params={"employee_id": f"eq.{employee_id}"})
        _supabase_request("DELETE", "error_logs", params={"employee_id": f"eq.{employee_id}"})
        _supabase_request("DELETE", "employees", params={"employee_id": f"eq.{employee_id}"})
        return True, "Employee and related records deleted."

    with get_connection() as conn:
        existing = conn.execute("SELECT employee_id FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
        if existing is None:
            return False, "Employee not found."

        conn.execute("BEGIN")
        conn.execute("DELETE FROM attendance_logs WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM verification_logs WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM error_logs WHERE employee_id = ?", (employee_id,))
        conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
        conn.commit()
    return True, "Employee and related records deleted."


def get_last_attendance_action(employee_id: str) -> Optional[str]:
    rows = get_employee_attendance(employee_id, limit=1)
    if not rows:
        return None
    return rows[0]["action"]


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
    if _using_supabase():
        _supabase_request(
            "POST",
            "attendance_logs",
            payload={
                "employee_id": employee_id,
                "action": action,
                "timestamp": now,
                "verified": bool(verified),
                "score": score,
            },
        )
        return

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
    if _using_supabase():
        _supabase_request(
            "POST",
            "verification_logs",
            payload={
                "employee_id": employee_id,
                "success": bool(success),
                "score": score,
                "message": message,
                "timestamp": now,
            },
        )
        if not success:
            _supabase_request(
                "POST",
                "error_logs",
                payload={
                    "employee_id": employee_id,
                    "score": score,
                    "message": message,
                    "timestamp": now,
                },
            )
        return

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO verification_logs (employee_id, success, score, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (employee_id, 1 if success else 0, score, message, now),
        )
        if not success:
            conn.execute(
                """
                INSERT INTO error_logs (employee_id, score, message, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (employee_id, score, message, now),
            )


def get_recent_attendance(limit: int = 100) -> List[Dict[str, Any]]:
    if _using_supabase():
        rows = _to_row_list(
            _supabase_request(
                "GET",
                "attendance_logs",
                params={
                    "select": "id,employee_id,action,timestamp,verified,score,employees(full_name)",
                    "order": "id.desc",
                    "limit": limit,
                },
            )
        )
        normalized: List[Dict[str, Any]] = []
        for row in rows:
            normalized.append(
                {
                    "id": row.get("id"),
                    "employee_id": row.get("employee_id"),
                    "full_name": ((row.get("employees") or {}).get("full_name") if isinstance(row.get("employees"), dict) else None),
                    "action": row.get("action"),
                    "timestamp": row.get("timestamp"),
                    "verified": 1 if row.get("verified") else 0,
                    "score": row.get("score"),
                }
            )
        return normalized

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
    return [dict(row) for row in rows]


def get_employee_attendance(employee_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    if _using_supabase():
        return _to_row_list(
            _supabase_request(
                "GET",
                "attendance_logs",
                params={
                    "select": "id,employee_id,action,timestamp,verified,score",
                    "employee_id": f"eq.{employee_id}",
                    "order": "id.desc",
                    "limit": limit,
                },
            )
        )

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
    return [dict(row) for row in rows]


def get_recent_verification_errors(limit: int = 100) -> List[Dict[str, Any]]:
    return get_recent_errors(limit=limit)


def get_recent_verifications(limit: int = 200) -> List[Dict[str, Any]]:
    if _using_supabase():
        return _to_row_list(
            _supabase_request(
                "GET",
                "verification_logs",
                params={
                    "select": "id,employee_id,success,score,message,timestamp",
                    "order": "id.desc",
                    "limit": limit,
                },
            )
        )

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
    return [dict(row) for row in rows]


def update_verification_log(
    log_id: int,
    employee_id: Optional[str],
    success: bool,
    score: Optional[float],
    message: str,
    timestamp: str,
) -> Tuple[bool, str]:
    if not message.strip():
        return False, "Message is required."
    if not _parse_iso_or_none(timestamp):
        return False, "Timestamp must be ISO format: YYYY-MM-DDTHH:MM:SS"
    if employee_id and not employee_exists(employee_id):
        return False, "Employee ID does not exist."

    if _using_supabase():
        existing = _supabase_request("GET", "verification_logs", params={"select": "id", "id": f"eq.{log_id}", "limit": 1})
        if not existing:
            return False, "Verification log not found."
        _supabase_request(
            "PATCH",
            "verification_logs",
            params={"id": f"eq.{log_id}"},
            payload={
                "employee_id": employee_id,
                "success": bool(success),
                "score": score,
                "message": message.strip(),
                "timestamp": timestamp,
            },
        )
        return True, "Verification log updated."

    with get_connection() as conn:
        row = conn.execute("SELECT id FROM verification_logs WHERE id = ?", (log_id,)).fetchone()
        if row is None:
            return False, "Verification log not found."
        conn.execute(
            """
            UPDATE verification_logs
            SET employee_id = ?, success = ?, score = ?, message = ?, timestamp = ?
            WHERE id = ?
            """,
            (employee_id, 1 if success else 0, score, message.strip(), timestamp, log_id),
        )
    return True, "Verification log updated."


def update_error_log(
    log_id: int,
    employee_id: Optional[str],
    score: Optional[float],
    message: str,
    timestamp: str,
) -> Tuple[bool, str]:
    if not message.strip():
        return False, "Message is required."
    if not _parse_iso_or_none(timestamp):
        return False, "Timestamp must be ISO format: YYYY-MM-DDTHH:MM:SS"
    if employee_id and not employee_exists(employee_id):
        return False, "Employee ID does not exist."

    if _using_supabase():
        existing = _supabase_request("GET", "error_logs", params={"select": "id", "id": f"eq.{log_id}", "limit": 1})
        if not existing:
            return False, "Error log not found."
        _supabase_request(
            "PATCH",
            "error_logs",
            params={"id": f"eq.{log_id}"},
            payload={
                "employee_id": employee_id,
                "score": score,
                "message": message.strip(),
                "timestamp": timestamp,
            },
        )
        return True, "Error log updated."

    with get_connection() as conn:
        row = conn.execute("SELECT id FROM error_logs WHERE id = ?", (log_id,)).fetchone()
        if row is None:
            return False, "Error log not found."
        conn.execute(
            """
            UPDATE error_logs
            SET employee_id = ?, score = ?, message = ?, timestamp = ?
            WHERE id = ?
            """,
            (employee_id, score, message.strip(), timestamp, log_id),
        )
    return True, "Error log updated."


def update_attendance_log(
    log_id: int,
    employee_id: str,
    action: str,
    verified: bool,
    score: Optional[float],
    timestamp: str,
) -> Tuple[bool, str]:
    normalized_action = action.strip().upper()
    if normalized_action not in {"TIME_IN", "TIME_OUT"}:
        return False, "Action must be TIME_IN or TIME_OUT."
    if not _parse_iso_or_none(timestamp):
        return False, "Timestamp must be ISO format: YYYY-MM-DDTHH:MM:SS"
    if not employee_exists(employee_id):
        return False, "Employee ID does not exist."

    if _using_supabase():
        existing = _supabase_request("GET", "attendance_logs", params={"select": "id", "id": f"eq.{log_id}", "limit": 1})
        if not existing:
            return False, "Attendance log not found."
        _supabase_request(
            "PATCH",
            "attendance_logs",
            params={"id": f"eq.{log_id}"},
            payload={
                "employee_id": employee_id,
                "action": normalized_action,
                "verified": bool(verified),
                "score": score,
                "timestamp": timestamp,
            },
        )
        return True, "Attendance log updated."

    with get_connection() as conn:
        row = conn.execute("SELECT id FROM attendance_logs WHERE id = ?", (log_id,)).fetchone()
        if row is None:
            return False, "Attendance log not found."
        conn.execute(
            """
            UPDATE attendance_logs
            SET employee_id = ?, action = ?, verified = ?, score = ?, timestamp = ?
            WHERE id = ?
            """,
            (employee_id, normalized_action, 1 if verified else 0, score, timestamp, log_id),
        )
    return True, "Attendance log updated."


def get_recent_errors(limit: int = 300) -> List[Dict[str, Any]]:
    if _using_supabase():
        return _to_row_list(
            _supabase_request(
                "GET",
                "error_logs",
                params={"select": "id,employee_id,score,message,timestamp", "order": "id.desc", "limit": limit},
            )
        )

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, employee_id, score, message, timestamp
            FROM error_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_daily_summary(manager_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if _using_supabase():
        rows = get_recent_attendance(limit=5000)
        
        if manager_id is not None:
            # Filter rows by manager_id locally since we don't have employees table join in this simple summary query
            from storage import get_employee
            managed_emp_ids = {u["employee_id"] for u in list_employees(manager_id)}
            rows = [r for r in rows if r.get("employee_id") in managed_emp_ids]

        by_day: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            day = str(row["timestamp"]).split("T", 1)[0]
            if day not in by_day:
                by_day[day] = {"day": day, "total_time_in": 0, "total_time_out": 0, "total_actions": 0}
            by_day[day]["total_actions"] += 1
            if row["action"] == "TIME_IN":
                by_day[day]["total_time_in"] += 1
            elif row["action"] == "TIME_OUT":
                by_day[day]["total_time_out"] += 1
        return [by_day[key] for key in sorted(by_day.keys(), reverse=True)]

    with get_connection() as conn:
        if manager_id is not None:
            rows = conn.execute(
                """
                SELECT
                    date(a.timestamp) AS day,
                    SUM(CASE WHEN a.action = 'TIME_IN' THEN 1 ELSE 0 END) AS total_time_in,
                    SUM(CASE WHEN a.action = 'TIME_OUT' THEN 1 ELSE 0 END) AS total_time_out,
                    COUNT(*) AS total_actions
                FROM attendance_logs a
                INNER JOIN employees e ON a.employee_id = e.employee_id
                WHERE e.manager_id = ?
                GROUP BY date(a.timestamp)
                ORDER BY day DESC
                """,
                (manager_id,)
            ).fetchall()
        else:
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
    return [dict(row) for row in rows]
