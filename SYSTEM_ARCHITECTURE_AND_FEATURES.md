# 21 Void Technologies — System Architecture & Feature Reference

> **Authoritative Specification & Architecture Guide**  
> *Note for all developers and AI coding agents: Review this document before proposing or applying code modifications to maintain system integrity and prevent architectural regressions.*

---

## 1. Core Architectural Standards & Iron Rules

1. **Zero Django Forms**:
   - Never introduce `django.forms.Form` or `ModelForm`.
   - All forms are 100% semantic HTML templates processed via Function-Based Views (FBVs).
   - Form submission and validation is performed explicitly in Python FBVs using helper parsing utilities in `core/validators.py`.

2. **100% Function-Based Views (FBVs)**:
   - Strictly avoid Class-Based Views (CBVs) or Generic Views (`ListView`, `CreateView`, `UpdateView`).
   - Keep views concise, readable, and decoupled.

3. **Uniform JSON Envelope Response**:
   - All AJAX mutation endpoints must return a standardized JSON envelope via `core/responses.py`:
     ```python
     return success_response(title="Success Title", message="User-friendly message", data={...})
     return error_response(title="Error Title", message="Actionable error description", errors={...})
     ```
   - The JSON envelope guarantees:
     - `status`: `"success"` or `"error"`
     - `icon`: `"success"`, `"error"`, `"warning"`, or `"info"`
     - `title`: Short title for alerts/modals
     - `message`: Descriptive user feedback
     - `data`: Optional payload dictionary (e.g. `{ 'reload': True }`)

4. **Global Authentication & Security**:
   - Protected by `core.middleware.GlobalLoginRequiredMiddleware`.
   - All endpoints require authentication by default.
   - Publicly exempt paths: `/accounts/login/`, `/accounts/logout/`, `/static/`, `/media/`, and `/admin/login/`.
   - Unauthenticated AJAX requests automatically receive `401 Unauthorized` with `{ "status": "error", "message": "Authentication required. Please log in." }`.

---

## 2. Standard Design & Button System

All buttons across tables, cards, modals, and toolbars MUST strictly adhere to the unified button design system:

| Button Class | Visual Styling | Primary Use Case |
| :--- | :--- | :--- |
| `.btn-primary` | Solid Blue (`bg-blue-600` hover `bg-blue-700`, white text, rounded-xl, font-bold) | Primary actions (Save, Submit, Complete Checkout, Create) |
| `.btn-secondary`| Slate gray / subtle blue (`bg-slate-100` hover `bg-slate-200`, slate-700 text) | Secondary actions (Cancel, Back, Close modal) |
| `.btn-default`  | Bordered slate (`border border-slate-300`, slate-700 text, hover `bg-slate-50`) | Neutral actions (Reset, Clear, Export secondary) |
| `.btn-danger`   | Solid red / deep red (`bg-red-600` hover `bg-red-700`, white text) | Destructive actions (Delete confirmation, Purge, Clean Overwrite) |

### Dashboard Contrast Rules
- Dashboard metric cards use light blue / pastel backgrounds (`bg-blue-50`, `bg-sky-50`, `bg-indigo-50`, etc.).
- Text on dashboard cards **must always be bold navy blue** (`text-[#0b192c]`, `text-blue-950`, `text-blue-900`) — **never white**.
- Topbar navigation dropdowns (User Profile, Notifications) strictly use navy blue text for optimal readability.

### Viewport & Table Scroll Architecture
- The main content block (`{% block content %}`) fits the viewport screen height.
- Tables scroll internally within `.overflow-y-auto .custom-scrollbar`.
- Table headers (`<thead>`) are sticky (`sticky top-0 z-20 bg-slate-100`) so column titles remain pinned while rows scroll.

---

## 3. Global JavaScript Helpers & Modals (`static/js/app.js`)

The following utilities are exported directly to `window` for reliable AJAX interactions:

- **`window.notifySwal(title, message, icon, timer)`**: Displays a SweetAlert2 notification popup.
- **`window.confirmSwal(title, text, confirmBtnText, onConfirm)`**: Standardized SweetAlert2 confirmation dialog.
- **`window.showNotification(message, icon)`**: Direct shorthand alert for user feedback.
- **`window.closeModal()`**: Closes the active modal shell safely.
- **`window.refreshTable(tableSelector)`**: AJAX reloads a partial table container without refreshing the browser.
- **`window.paginateTable(containerSelector, pageNumber)`**: AJAX paginates table partials.
- **`window.initSearchableCombobox(selector)`**:
  Universal combobox with keyboard arrow support:
  - `ArrowDown` / `ArrowUp`: Navigates through filtered list with auto-scroll.
  - `Enter`: Selects highlighted item.
  - `Escape`: Closes dropdown.
  - Real-time typing filter with click-away dismissal.
  - Triggers `combobox:selected` event with `[id, name, dataset]`.

---

## 4. Key Module Implementations

### A. Point of Sale (POS) & Multi-Item Checkout
- **Customer Selection**: Optional. If omitted, automatically defaults to `Customer.get_default_customer()` ("Walk-in Customer").
- **Cart Interaction**: On product selection / add-to-cart, the product search input immediately clears and regains focus for high-speed barcode or manual entry.
- **Instant Receipts**: Generates professional PDF receipts via ReportLab (`sales/views.py:receipt_pdf_view`). Logo renders with transparent background (`mask='auto'`).
- **Outstanding Sidebar Button**: The POS navigation button has an animated badge, subtle glow, and stands out prominently.

### B. Inventory Management & 3-Step Invoice Wizard
- **3-Step Wizard Intake (`templates/inventory/partials/receive_invoice_modal.html`)**:
  - Step 1: Invoice Details (Supplier combobox with arrow keys, invoice #, date received).
  - Step 2: Invoice Items (Product searchable combobox with arrow keys, unit quantity, cost, selling price).
  - Step 3: Verification & Preview (Comprehensive summary cards, itemized cost total, submit button).
- **FIFO Batch Valuation**: Product valuation calculates accurate totals from active batches (`Product.stock_value` and `Product.total_cost_value`).
- **Product Details Modal**: Displays full batch inventory history, unit costs, and supplier references.

### C. Low Stock Alerts & Notifications
- **Header Dropdown**: Styled with distinct blue text color (`text-blue-900`, `text-blue-800`, `text-blue-700`).
- **Respective Reorder Level Color Coding**:
  Dynamically calculated via `Notification.stock_level_data` based on $Q / R$ (Quantity Available / Reorder Quantity):
  - `0% Remaining` ($Q = 0$): **Critical Red** (`bg-red-500 text-white`, bar `bg-red-500`, label `Depleted (0%)`)
  - `1% - 25% Remaining`: **Rose / Crimson** (`bg-rose-600 text-white`, bar `bg-rose-500`, label `Critical ({pct}%)`)
  - `26% - 50% Remaining`: **Orange** (`bg-orange-600 text-white`, bar `bg-orange-500`, label `Urgent ({pct}%)`)
  - `51% - 75% Remaining`: **Amber** (`bg-amber-600 text-white`, bar `bg-amber-500`, label `Low ({pct}%)`)
  - `76% - 100% Remaining`: **Yellow** (`bg-yellow-600 text-white`, bar `bg-yellow-500`, label `Reorder ({pct}%)`)
- **Visual Progress Gauges**: Both the header dropdown and the main notification table feature mini visual progress bands indicating the exact proportion of stock remaining.
- **Direct Modal Inspection**: Clicking any stock alert item directly opens `inventory:product_detail_modal` with complete batch history without redirecting away from the view.

### D. Operational Expenses & Automated Recurring Engine
- **Categories**: Configured with `default_amount`, `is_recurring`, and `recurring_interval` (`DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`).
- **Auto-Fill**: Selecting an expense category in the modal automatically pre-populates the amount field if a default amount exists.
- **Auto-Recurring Engine**: `sync_recurring_expenses()` automatically evaluates due recurring categories upon accessing expenses or reports and posts scheduled records.

### E. Universal Database Backup & Restore Engine
- **Download**:
  - **Universal JSON Backup** (`dumpdata` with natural keys and clean exclusions): Cross-platform data portability across **SQLite**, **PostgreSQL**, and **Docker**.
  - **Raw SQLite Binary**: Direct download of `.sqlite3` file when running in SQLite environments.
- **Restore / Import**:
  - **Live Progress Band**: Tracks client-to-server file upload via `xhr.upload.onprogress` and animates across 4 structured phases: *Upload $\rightarrow$ Validate $\rightarrow$ Ingest Data $\rightarrow$ Finalize*.
  - **Comprehensive Response Card**: Reports metadata including format, file size, restoration mode, execution duration in seconds, total records restored, and a badge breakdown of all imported model entities.
  - **Overwrite Mode**: Atomically cleans application tables in reverse-dependency order before executing `loaddata`.
  - **Merge Mode**: Ingests fixture records directly into the existing database.
  - Complete `transaction.atomic()` safety with automatic rollback upon format or database integrity failures.

---

## 5. Developer Verification & Regression Checklist

Before committing any future changes, always verify:
1. `python manage.py check` executes with 0 errors.
2. Unauthenticated access to any protected route redirects to `/accounts/login/`.
3. Dashboard metric cards maintain light backgrounds with dark navy blue text.
4. Receipt PDF generation displays company logo with clean alpha transparency.
5. All modals close properly when clicking Cancel or the cross button (`window.closeModal()`).
6. Custom searchable comboboxes filter items and respond to keyboard arrow keys (`ArrowDown`, `ArrowUp`, `Enter`).
7. Database backup export generates valid JSON fixtures that restore cleanly in both Merge and Overwrite modes.
