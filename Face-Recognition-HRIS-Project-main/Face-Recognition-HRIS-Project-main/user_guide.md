# Face Recognition HRIS - User Guide

Welcome to the Face Recognition HRIS App. This manual is a broad starting point to understanding what the system does and how to easily use it day-to-day.

## What Does This App Do?
The app is a Human Resources Information System (HRIS). It tracks employees clocking in and out (attendance). Setting it apart is the built-in Face Recognition - it actually scans your face to securely log you in ensuring it's actually you clocking your own time! It contains two environments: an Employee app to clock your time, and a separate Admin app to manage records behind the scenes.

## Getting Started and the Main Dashboard

When you open the central Employee application (`main.py`), you'll be greeted by the **Navigation Window**.

### Step 1: Logging In or Making an Account
- **New Employees**: Click the Employee Login/Signup tab. On the right side, carefully enter your exact details (ID, Name, Department, Role, Phone, Email). Ensure every box is filled correctly, then select "Create Account".
- **Existing Employees**: Look at the left side ("Login"), type your Employee ID, and press the login button.

**What happens next**: Once logged in securely, the top bar will display your name. You can now access the restricted tabs like the Biometric verification page and Log views.

### Step 2: Setting up Facial Biometrics (Enrolling)
If this is your first time:
- Move to the **Biometric Workspace** Tab.
- Sit comfortably in front of the camera, ensuring good lighting.
- Press **Start Enrollment**. The app will snap precisely 10 clear photos over a few seconds, turning your facial structure into a secure mathematical template saved only internally for you. 
- Wait for the "Success" confirmation popup.

### Step 3: Clocking In and Out properly
Once enrolled, your general day starts here:
- Open the **Biometric Workspace**.
- If logging your start of the day, press the huge **Time In** button.
- The camera begins reading. Maintain a steady look at the lens. Once it recognizes your distinct facial features matching your registered template, your check-in time saves permanently.
- Simply do the exact same but choosing **Time Out** when your shift is over.

---

## Setting up the Manager Portal & SysAdmin Secret

The Employee Application (`main.py`) handles regular workers, but the Admin Application (`admin_app.py`) is strictly for managers. Before any manager can log in, you must designate the very first one using the **SysAdmin Secret**.

1. **Prerequisite**: Use `main.py` to register a standard employee account first (e.g. ID `MGR-01`).
2. **Open the Admin App**: Launch `admin_app.py` and click **Register Manager**.
3. **The SysAdmin Secret**: You will be asked for a `SysAdmin Secret`. The very first time you launch the Admin App, it will securely auto-generate this secret, save it into your `.env` file, and display it in a welcome popup.
4. **Upgrade Account**: Enter the secret, type the existing `Employee ID`, and give them a brand-new Admin Password. 
5. That employee is now a Manager! They can log in normally via `admin_app.py` using their ID and that new password.

## Manager Duties and Team Viewing

Once logged into `admin_app.py` as a manager, you'll see the **Admin Panel**.

- **Team Control**: Managers do *not* see everyone. If an employee has your Manager ID set in their records, they appear on your list. Otherwise, they are hidden.
- **Editing Schedules**: You can update when your employees are meant to start and end their shifts (e.g. typing `09:00` in their `schedule_time_in` field). 
- **Self-Editing Rule**: For security, while you oversee your team's logs, you are strictly unable to click and edit *your own* profile using your own Manager App.

---

## Your Employee Logs

Curious how often you've been late, or tracking potential overtime limits? The **Employee Logs** tab provides an accurate view.

Inside that tab, you can:
- Observe a chronologically ordered table listing every single check-in you've done.
- Open the **Log Summary Chart**, an interactive visual graph.
- Using this graph, use the switches at the top to highlight "Time In" statistics or "Time Out" statistics.
- Hover your mouse precisely over any blue or orange dot to view the exact time/date that entry registered!
- Red flags let you know if you've missed a standard timestamp window (e.g. 9 AM start, 5 PM Finish). 

## Warnings and Errors: What Do They Mean?

- **"Access Denied" or red highlights**: You made an error when typing an Employee ID or an email syntax was incorrect. Retype clearly.
- **"Face Not Matched" / "Impostor Margin"**: You tried to verify your face, but lighting was too dark, or a heavy motion-blur shifted your read, or someone else looked into the camera. Do NOT panic. Press check-in again, wait for clear lighting, and face the camera directly.
- **Cannot click tabs**: Unless you log in first with a valid ID, other tabs are legally locked and blocked from being interacted with. 

## The Admin Space
Only designated Administrators have permission here. They access the `admin_app.py` executable completely isolated from standard users.
There they type secure admin credentials they established to correct discrepancies securely, delete ex-employees entirely, and ensure logging practices are properly audited.