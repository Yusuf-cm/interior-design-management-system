




Studio.OS | Interior Decor Business Management
Studio.OS is a professional-grade, full-stack operational management platform designed specifically for interior design boutique firms. It replaces scattered spreadsheets and messy paperwork with a centralized, secure, and visually stunning "command center" for business owners and design teams.
🚀 Live Demo
Frontend: [Your Vercel URL Here]
Backend API: [Your Render URL Here]
🧠 The Problem It Solves
Independent designers and small studios often struggle with fragmented data. Client contact info is in one place, project statuses in another, and financial balances are buried in bank statements.
Studio.OS solves this by:
Centralizing Operations: Linking every project directly to a client and a staff member.
Financial Clarity: Providing real-time tracking of "Estimated Cost" vs. "Actual Payments," automatically calculating outstanding balances.
Role-Based Security: Ensuring staff only see what they need to work on, while admins maintain the "Big Picture" view.
👥 Who It’s For
Boutique Interior Design Studios: Manage multiple designers and high-value projects.
Independent Design Consultants: Track client history and financial health.
Project Managers: Oversee the lifecycle of renovations from "Pending" to "Settled."
🛠 Tech Stack
Frontend
React (Vite): High-performance Single Page Application (SPA).
Mantine UI: A professional component library for a "Glassmorphism" luxury aesthetic.
Framer Motion: Smooth, staggered animations for an organic UI feel.
Axios: Interceptor-based API management for secure JWT handling.
Backend
Django REST Framework: A robust "Headless API" architecture.
PostgreSQL 18: Enterprise-grade relational database for data integrity.
SimpleJWT: Secure, stateless authentication.
WhiteNoise: High-performance static file serving.
🏗 System Architecture
The system uses a Decoupled Architecture:
Headless API: The Django backend acts strictly as a data provider, returning JSON. This allows for future expansion into mobile apps (iOS/Android) without rewriting logic.
State-Driven UI: The React frontend manages its own view-states and filters data in real-time using Django’s backend SearchFilter and OrderingFilter.
Data Siloing: Implemented at the database query level (get_queryset). If a user is not an Admin, the database only reveals records assigned to that specific user ID.
🌟 Feature List
Executive Dashboard: Total revenue tracking, active project counts, and recent activity feeds.
Permanent Project Records: Once a project is launched, the Client and Title are locked to prevent record tampering.
Client Registry: A searchable, filterable CRM for managing client contact details and history.
Workflow Management: Track jobs through four states: Pending, Active, Completed, and Cancelled.
Financial Progress Tracking: Visual progress bars showing the percentage of the contract value paid to date.
Staff Onboarding: Admin-only interface for registering new team members and assigning roles.
📦 Deployment
Backend (Render)
Environment: Python 3.13.1.
Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
Start Command: gunicorn core.wsgi:application --timeout 120
Database: Managed PostgreSQL instance.
Frontend (Vercel)
Framework: Vite.
Build Command: npm run build.
Environment Variables: VITE_API_URL pointing to the Render API endpoint.
🛠 Installation (Local Development)
Clone the repo: git clone <repo-url>
Backend Setup:
code
Bash
cd interior_management
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
Frontend Setup:
code
Bash
cd frontend
npm install
npm run dev
📊 Business Logic Implementation (Teacher's Notes)
Money Handling: Uses DecimalField (not Float) to ensure 100% mathematical accuracy for financial totals.
Custom User Model: Built using AbstractUser to allow for Admin vs Staff roles from day one.
JWT Interceptors: Automatically attaches Authorization headers to all outgoing requests to ensure a seamless "Logged In" experience.
Developed with 🖤 for the Interior Design Industry.