Studio.OS | Interior Decor Business Management
Studio.OS is a professional-grade, full-stack operational management platform designed specifically for interior design boutique firms. It replaces scattered spreadsheets and messy paperwork with a centralized, secure, and visually stunning "command center" for business owners and design teams.
🚀 Live Demo
Frontend: [https://interior-design-management-system-6ytdzrf9u.vercel.app/]
Demo credentials
:username-admin
 password-TemporaryPassword123!
Backend API: [https://interior-design-management-system.onrender.com]
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
<img width="359" height="406" alt="Screenshot 2026-02-15 at 20 59 54" src="https://github.com/user-attachments/assets/1c5b6bd9-1c30-400b-aaa2-acd1730140d3" />
<img width="351" height="401" alt="Screenshot 2026-02-15 at 20 59 35" src="https://github.com/user-attachments/assets/5b43affd-56ae-4759-848e-fac30c35e4be" />
<img width="1439" height="812" alt="Screenshot 2026-02-15 at 20 59 13" src="https://github.com/user-attachments/assets/a4763cb9-039d-47ed-9e30-a1c4d8f78ddd" />
<img width="393" height="608" alt="Screenshot 2026-02-15 at 20 58 50" src="https://github.com/user-attachments/assets/b728440d-f910-46f2-aab6-56d706771500" />
<img width="443" height="437" alt="Screenshot 2026-02-15 at 20 58 18" src="https://github.com/user-attachments/assets/36d5851c-4e0a-4f14-a4d3-e9cd5ff6d1a0" />
<img width="436" height="437" alt="Screenshot 2026-02-15 at 20 57 45" src="https://github.com/user-attachments/assets/4a72dc9c-056f-4595-bb9a-158241ce7b11" />
<img width="438" height="487" alt="Screenshot 2026-02-15 at 20 57 21" src="https://github.com/user-attachments/assets/afe352d1-e574-41c2-8290-8ebc258d7bae" />
<img width="1440" height="815" alt="Screenshot 2026-02-15 at 20 56 57" src="https://github.com/user-attachments/assets/ce89e189-38bd-4537-b968-c1b2594ac85e" />
<img width="1439" height="812" alt="Screenshot 2026-02-15 at 20 54 08" src="https://github.com/user-attachments/assets/e975fd16-8e01-4399-8bf1-1412049f174a" />
<img width="1439" height="815" alt="Screenshot 2026-02-15 at 20 53 35" src="https://github.com/user-attachments/assets/0df35e9e-55ba-4490-9dcb-47c02ed84203" />

