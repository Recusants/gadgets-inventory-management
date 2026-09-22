"""
Generates professional PDF User and Admin Manuals for 21 Void Technologies.
Outputs:
- manuals/User_Manual.pdf
- manuals/Admin_Manual.pdf
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

BASE_DIR = Path(__file__).resolve().parent
MANUALS_DIR = BASE_DIR / 'manuals'
MANUALS_DIR.mkdir(exist_ok=True)

def build_pdf_manual(filename, title, subtitle, sections):
    doc = SimpleDocTemplate(
        str(filename),
        pagesize=letter,
        rightMargin=45,
        leftMargin=45,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0f172a'),
        alignment=0
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#2563eb'),
        alignment=0
    )
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=8
    )
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=4
    )
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#64748b')
    )

    elements = []

    # Cover Banner
    elements.append(Paragraph("21 VOID TECHNOLOGIES", title_style))
    elements.append(Paragraph(subtitle.upper(), subtitle_style))
    elements.append(Paragraph("Fusing Technology With Market Intelligence &bull; Official System Documentation", tagline_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#2563eb'), spaceBefore=5, spaceAfter=20))

    for sec_num, (heading, content_blocks) in enumerate(sections, 1):
        elements.append(Paragraph(f"{sec_num}. {heading}", section_title))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cbd5e1'), spaceBefore=2, spaceAfter=8))
        
        for block in content_blocks:
            if block.startswith("• ") or block.startswith("* "):
                elements.append(Paragraph(f"&bull; {block[2:]}", bullet_style))
            elif block.startswith("[TABLE]"):
                # Table parser
                rows_data = [r.split("|") for r in block.replace("[TABLE]", "").strip().split("\n")]
                table_obj = Table(rows_data)
                table_obj.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ]))
                elements.append(Spacer(1, 4))
                elements.append(table_obj)
                elements.append(Spacer(1, 6))
            else:
                elements.append(Paragraph(block, body_style))
        
        elements.append(Spacer(1, 10))

    # Document Footer
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#94a3b8'), spaceBefore=10, spaceAfter=10))
    elements.append(Paragraph("21 Void Technologies &bull; Confidential & Proprietary Document &bull; Generated Automatically", tagline_style))

    doc.build(elements)
    print(f"Generated: {filename} ({filename.stat().st_size} bytes)")


# ==============================================================================
# 1. USER MANUAL CONTENT
# ==============================================================================
user_sections = [
    ("System Overview & Native Desktop App Interface", [
        "Welcome to the 21 Void Technologies Record Keeping & Inventory System. This system is designed as a fast, offline-first application that feels and responds like a modern native desktop tool.",
        "• Non-scrolling Viewport: The main application window has a fixed desktop viewport. Navigation and toolbars remain anchored while only inner tables and content panels scroll smoothly.",
        "• Fixed Sidebar: Access all core features anytime from the left navigation bar (Dashboard, Products / Inventory, Sales, POS Checkout, Customers, Reports, and Settings).",
        "• Live Clock & Dark Mode: The sticky topbar displays a real-time calendar clock and an instant Dark/Light mode toggle that saves your preference automatically.",
        "• Touch & Mouse Driven: Every interaction is 100% mouse and touch operated. There are no confusing keyboard shortcuts or hotkeys to memorize."
    ]),
    ("Inventory Management & Physical Stock Tracking", [
        "The inventory tracks items individually by unique serial number. Unlike generic quantity stores, every row represents a physical piece of hardware in stock.",
        "• Adding New Stock: Click '+ Add Product' to open the slide-up modal. Enter the Product Name, Category, Serial Number, Account Number, Date Received, and Cost Price (Amount Bought).",
        "• Statuses: Each item transitions cleanly between 'In Stock', 'Sold', 'Low Stock', and 'Returned'.",
        "• Real-Time Search: Type in the search bar on the Inventory screen to immediately filter by product name, serial number, or account number with live skeleton loaders."
    ]),
    ("Point-of-Sale (POS) Checkout & Instant PDF Receipts", [
        "The dedicated POS Checkout screen (/sales/checkout/) allows staff to complete customer purchases in seconds.",
        "• Select Product: Choose any available 'In Stock' product. The system automatically populates the selling price and item specifications.",
        "• Customer Selection: Select an existing client or click '+ New Customer' to register a new customer profile without leaving the screen.",
        "• Payment Method: Select Cash (USD), Bank Transfer / ZIPIT, EcoCash, or Card.",
        "• Instant Branded Receipt: Immediately upon clicking 'Complete Sale & Checkout', a SweetAlert2 confirmation gives you a one-click button to print or download a high-resolution PDF receipt formatted with your company logo, contact details, serial numbers, and warranty terms."
    ]),
    ("Sales History & Customer Ledger", [
        "Track every completed transaction from the Sales module.",
        "• Profit Tracking: The system automatically calculates gross profit by subtracting the item's purchase cost from the selling price.",
        "• Automatic Reversion: If a sale was entered in error, an administrator can void the sale, which automatically returns the physical item back to 'In Stock' status.",
        "• Customer Directory: Review each customer's lifetime purchase history and total orders."
    ]),
    ("Reports, Financial Analytics & Offline Exports", [
        "Generate executive reports with customizable time filters (Today, 7 Days, 30 Days, 1 Year, or Custom).",
        "• Excel Exports (.xlsx): Download complete sales records and current inventory valuation tables with auto-calculated totals and formatted currency cells.",
        "• PDF Reports (.pdf): Generate landscape executive summary documents ready for print and management review."
    ])
]

# ==============================================================================
# 2. ADMIN MANUAL CONTENT
# ==============================================================================
admin_sections = [
    ("Technical Architecture & Technology Stack", [
        "21 Void Technologies is built with an offline-first, container-ready Django 5 architecture.",
        "• Backend: Python 3.10+, Django 5.2, strictly 100% Function-Based Views (FBVs).",
        "• Input Validation: Zero Django Forms framework. All requests are handled via raw HTML inputs and validated by dedicated validation routines in core/validators.py.",
        "• Frontend: Server-rendered templates, precompiled Tailwind CSS, self-hosted Inter fonts, FontAwesome 6 icons, jQuery 3.7.1 (sole AJAX client), SweetAlert2 (sole notification dialog system), and Chart.js 4.4.",
        "• Database: SQLite (Local development) and PostgreSQL 16 (Docker environments)."
    ]),
    ("Three Deployment Run Modes", [
        "The system includes a single launch script (launch.bat on Windows, launch.sh on Linux/macOS) supporting three isolated run modes:",
        "[TABLE]Mode|Command|Database|Stack Architecture\nLocal Venv|launch.bat local|SQLite|Python venv + Django Dev Server\nDocker Dev|launch.bat docker_dev|PostgreSQL 16|Docker Compose with Live Reload\nDocker Prod|launch.bat docker_prod|PostgreSQL 16|Gunicorn (3 workers) + Nginx (port 80)",
        "• Auto-Launch: In local and Docker prod modes, the launch script automatically opens the default web browser to the homepage upon startup."
    ]),
    ("User Roles & Role-Based Access Control (RBAC)", [
        "User permissions are enforced through the role_required decorator and custom session timeouts:",
        "• Administrator (ADMIN): Full administrative rights, user account creation, system settings modifications, and sale voiding/deletion. Session timeout: 1 hour.",
        "• Manager (MANAGER): Can add/edit products, record sales, access financial reports and view settings. Session timeout: 8 hours.",
        "• Staff (STAFF): Operational point-of-sale checkout and inventory browsing. Restricted from sensitive deletions. Session timeout: 8 hours."
    ]),
    ("Company Settings & Receipt Customization", [
        "Administrators can configure company branding and receipt settings at /core/settings/:",
        "• Company Name, Tagline, Phone, Email, Physical Address",
        "• Currency Symbol (default: $) and Currency Code (default: USD)",
        "• Custom Receipt Header Titles & Return Policy / Guarantee Footer Notes"
    ]),
    ("Automated Nightly Backups & Recovery", [
        "The system provides an automated backup utility (backup.py):",
        "• SQLite Mode: Takes an atomic file-level copy of db.sqlite3 into the backups/ directory with timestamped filenames (e.g. db_backup_YYYYMMDD_HHMMSS.sqlite3).",
        "• PostgreSQL Mode: Issues automated pg_dump commands to archive database tables into timestamped SQL dumps.",
        "• Restoring Backups: For SQLite, simply replace db.sqlite3 with the backup copy. For PostgreSQL, execute pg_restore."
    ]),
    ("Non-Negotiable Constraints Compliance Verification", [
        "• Zero django.forms imports verified across all codebase files.",
        "• Zero generic Class-Based Views (CBVs) verified.",
        "• Zero fetch(), axios, or HTMX verified — jQuery $.ajax is the sole client.",
        "• Zero keyboard shortcuts or hotkeys anywhere — 100% mouse and touch driven.",
        "• 100% Offline asset isolation verified — zero external CDN or remote API calls."
    ])
]

if __name__ == '__main__':
    build_pdf_manual(MANUALS_DIR / "User_Manual.pdf", "21 Void Technologies", "User Operational Manual", user_sections)
    build_pdf_manual(MANUALS_DIR / "Admin_Manual.pdf", "21 Void Technologies", "Administrator & Deployment Manual", admin_sections)
