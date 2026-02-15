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
<img width="1439" height="815" alt="Screenshot 2026-02-15 at 20 53 35" src="https://github.com/user-attachments/assets/743e874a-af79-4190-985e-b3d9f4cbfd08" />
<img width="1439" height="812" alt="Screenshot 2026-02-15 at 20 54 08" src="https://github.com/user-attachments/assets/184f7ffe-24e3-4f8a-b671-0de263bcac8d" />
<img width="1440" height="815" alt="Screenshot 2026-02-15 at 20 56 57" src="https://github.com/user-attachments/assets/55c9ba77-88a3-44e6-a4fc-f315954c2087" />
<img width="438" height="487" alt="Screenshot 2026-02-15 at 20 57 21" src="https://github.com/user-attachments/assets/1ee48c04-1f55-4272-84b4-c26c6c157f89" />
<img width="436" height="437" alt="Screenshot 2026-02-15 at 20 57 45" src="https://github.com/user-attachments/assets/5e85e98b-82dd-4da1-a83b-692df7606e36" />
<img width="443" height="437" alt="Screenshot 2026-02-15 at 20 58 18" src="https://github.com/user-attachments/assets/ec58c1c2-1e36-4111-9772-f125d597762d" />
<img width="393" height="608" alt="Screenshot 2026-02-15 at 20 58 50" src="https://github.com/user-attachments/assets/e18d88c9-4039-4ddd-9d0a-54d5d96ffb01" />
<img width="1439" height="812" alt="Screenshot 2026-02-15 at 20 59 13" src="https://github.com/user-attachments/assets/f4b8decf-5ab7-48be-8bd7-08a96ebe94ea" />
<img width="351" height="401" alt="Screenshot 2026-02-15 at 20 59 35" src="https://github.com/user-attachments/assets/7268127d-8e4f-4adc-a6c9-f8fb11f893a3" />
<img width="359" height="406" alt="Screenshot 2026-02-15 at 20 59 54" src="https://github.com/user-attachments/assets/8ab1ef3d-8ffe-4ad8-a229-8c46a26209df" />

