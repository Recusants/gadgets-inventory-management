# Gadget Store Management System (21 Void Technologies)

A production-grade, high-performance retail inventory, Point-of-Sale (POS), and operational expense management platform built with Python, Django 5, PostgreSQL, Tailwind CSS, and Docker.

---

## Table of Contents
1. [Production Server Quickstart (Docker Hub Pull Mode)](#1-production-server-quickstart-docker-hub-pull-mode)
2. [Creating a Superuser on Production](#2-creating-a-superuser-on-production)
3. [User Roles & Access Control (RBAC)](#3-user-roles--access-control-rbac)
4. [Windows Auto-Start on System Boot](#4-windows-auto-start-on-system-boot)
5. [Routine Maintenance & Updates](#5-routine-maintenance--updates)
6. [Native Windows Deployment (Without Docker)](#6-native-windows-deployment-without-docker)
7. [Database Backup & Restore](#7-database-backup--restore)

---

## 1. Production Server Quickstart (Docker Hub Pull Mode)

The production environment is pre-configured to run isolated via Docker containers without requiring Python or development toolchains installed on the host machine.

- **Production Directory**: `C:\avail\gadget-store\`
- **Application URL**: `http://127.0.0.1:8086`
- **Docker Image**: `tinashemp/gadget-store-app:latest`

### Running the System
From `C:\avail\gadget-store\`:
```powershell
docker compose -f docker-compose.deploy.yml up -d
```

### Containers
| Container Name | Role | Ports |
| :--- | :--- | :--- |
| `gadget_store_prod_web` | Django Web Application & Gunicorn | Internal `8000` |
| `twentyone_void_prod_db` | PostgreSQL 16 Alpine Database | Internal `5432` |
| `twentyone_void_prod_nginx`| Nginx High-Speed Reverse Proxy & Static Cache | Host `8086:80` |

---

## 2. Creating a Superuser on Production

After launching the production server, create an administrator account using one of the following methods:

### Method 2: Direct Docker Command (Recommended & Used in Production)
Run this command from PowerShell or Command Prompt on the production machine:

```powershell
docker exec -it gadget_store_prod_web python manage.py createsuperuser
```

Or using Docker Compose:
```powershell
docker compose -f docker-compose.deploy.yml exec web python manage.py createsuperuser
```

#### What to enter during the prompt:
1. **Username**: Enter your admin username (e.g. `admin`).
2. **Email address**: Enter your email (or press Enter to skip).
3. **Password**: Type your password (characters will not be displayed on screen).
4. **Password (again)**: Confirm your password.

> **Note**: Superusers automatically receive the `ADMIN` role upon creation, giving immediate access to the **User Management Table**, database management, system settings, and executive telemetry.

---

### Method 1: Double-Click Helper Script (`create_superuser.bat`)
A helper script is provided in the root directory:
1. Navigate to `C:\avail\gadget-store\`
2. Double-click **`create_superuser.bat`**
3. The script auto-detects running Docker containers and opens the interactive `createsuperuser` prompt.

---

### Method 3: Native Windows Setup (Without Docker)
If running directly on Windows with Python venv:
```powershell
cd C:\avail\gadget-store
.\venv\Scripts\python.exe manage.py createsuperuser
```

---

### First Launch: Mandatory System Initialization & Setup Wizard

> **Production Notice**: Production databases do not use dummy seed data. All production data must be real, company-specific records provided by your administrator.

When you first log in after creating a superuser, the application automatically evaluates whether mandatory foundational data exists. If any mandatory records are missing, the system will **aggressively prompt** with an unclosable setup wizard modal:

| Mandatory Requirement | Why The System Requires It | Where Configured |
| :--- | :--- | :--- |
| **1. Company Profile & Logo** | Printed receipts, invoices, currency formatting, store branding. | Setup Wizard or **Settings $\rightarrow$ Company Settings** |
| **2. Product Category** | The system strictly requires at least 1 category to catalog inventory. | Setup Wizard, **Inventory $\rightarrow$ Categories**, or **+ Quick Category** |
| **3. Registered Supplier** | Required to receive inventory invoices and track FIFO batch costs. | Setup Wizard, **Inventory $\rightarrow$ Suppliers**, or Invoice Wizard |
| **4. Default Customer** | Counter sales at Point of Sale require a customer ("Walk-in Customer"). | Setup Wizard or **Sales $\rightarrow$ Customers** |
| **5. Expense Category** | Operational expenses require a category to compute net profit. | Setup Wizard or **Expenses $\rightarrow$ Categories** |

Completing the wizard configures your store profile, uploads your custom company logo (rendered on sales receipts and topbar), and calibrates the database for operations.

---

## 3. User Roles & Access Control (RBAC)


The application enforces a 3-tier Role-Based Access Control hierarchy:

| Role | Permissions |
| :--- | :--- |
| **`ADMIN`** / Superuser | Full system access. Can view/create/edit/deactivate users, manage database backups, view financial profit/loss analytics, and configure system settings. |
| **`MANAGER`** | Can manage inventory, receive purchase invoices, approve stock batches, view sales and expense reports, and operate POS. |
| **`STAFF`** | Limited to Point of Sale (POS) checkouts, viewing product stock levels, and recording basic customer records. |

### Accessing User Management
- Navigate to **Sidebar $\rightarrow$ Users** (or Profile Dropdown $\rightarrow$ **User Management**).
- Accessible strictly by `ADMIN` accounts or superusers.
- Includes debounced real-time search, role filters, active status toggles, and self-lockout safeguards (admins cannot deactivate or delete their own active account).

---

## 4. Windows Auto-Start on System Boot

To ensure the Gadget Store system starts automatically whenever the computer powers on:

### For Docker Deployment:
Docker Desktop / Docker engine containers are configured with `restart: always`. Once started, Docker will automatically relaunch the containers after a system reboot as long as Docker service is running.

### For Native Windows Deployment:
Run the installer script in the production folder:
```powershell
install_auto_start_on_boot.bat
```
- Adds a background task to the Windows Startup folder via `start_background_silent.vbs`.
- Launches Waitress silently in the background on port `8086`.
- To disable auto-start, double-click `uninstall_auto_start.bat`.

---

## 5. Routine Maintenance & Updates

### Pulling Application Updates
When a new version is pushed to Docker Hub via GitHub Actions:
```powershell
update_server.bat
```
Or manually:
```powershell
docker compose -f docker-compose.deploy.yml pull
docker compose -f docker-compose.deploy.yml up -d
```

### Stopping the Server
```powershell
docker compose -f docker-compose.deploy.yml down
```
*(Or run `stop_server.bat` for native Windows server)*

---

## 6. Native Windows Deployment (Without Docker)

If running the application directly on Windows without Docker containers:
1. Ensure Python 3.12+ is installed and a virtual environment is created (`python -m venv venv`).
2. Install dependencies: `pip install -r requirements.txt`
3. Launch the server:
   ```powershell
   run_server.bat
   ```
   This runs migrations, collects static assets, and boots the multi-threaded Waitress WSGI server on `http://127.0.0.1:8086`.

---

## 7. Database Backup & Restore

Accessible by Administrators under **Settings $\rightarrow$ Backup & Restore**:
- **Universal JSON Export**: Cross-platform format compatible with PostgreSQL, SQLite, and Docker environments.
- **Restore / Import**:
  - Live 4-phase progress band (*Upload $\rightarrow$ Validate $\rightarrow$ Ingest Data $\rightarrow$ Finalize*).
  - Supports **Merge Mode** (appends non-conflicting records) and **Overwrite Mode** (cleans existing data with transactional safety).
  - Detailed telemetry report card upon completion with one-click reload.
