# Studio.OS | Interior Decor Business Management

**Studio.OS** is a professional-grade, full-stack operational management platform designed specifically for interior design boutique firms. It replaces scattered spreadsheets and fragmented workflows with a centralized, secure, and visually refined command center for business owners and design teams.

---

## 🚀 Live Demo

**Frontend Application**
https://interior-design-management-system-6ytdzrf9u.vercel.app/

**Demo Credentials**
Username: `admin`
Password: `TemporaryPassword123!`

**Backend API**
https://interior-design-management-system.onrender.com

---

## 🧠 The Problem It Solves

Independent designers and small studios often operate with fragmented information:

* Client contacts stored in separate tools
* Project progress tracked inconsistently
* Financial balances scattered across records

This leads to poor visibility, delayed decisions, and operational inefficiency.

---

## ✅ The Solution

Studio.OS unifies operations into a single structured system:

* **Centralized Operations**
  Every project is linked directly to a client and assigned staff member.

* **Financial Clarity**
  Real-time comparison of estimated project cost vs. actual payments, with automatic outstanding balance calculation.

* **Role-Based Security**
  Staff access only relevant data while administrators maintain full operational visibility.

---

## 👥 Who It’s For

* Boutique interior design studios managing multiple designers and high-value projects
* Independent design consultants tracking client relationships and financial performance
* Project managers overseeing renovation lifecycles from planning to settlement

---

## 🖥 Interface Preview

### Executive Dashboard

<img src="https://github.com/user-attachments/assets/a4763cb9-039d-47ed-9e30-a1c4d8f78ddd" width="900">

<img src="https://github.com/user-attachments/assets/e975fd16-8e01-4399-8bf1-1412049f174a" width="900">

---

### Project Workflow & Operations

<img src="https://github.com/user-attachments/assets/ce89e189-38bd-4537-b968-c1b2594ac85e" width="900">

<img src="https://github.com/user-attachments/assets/0df35e9e-55ba-4490-9dcb-47c02ed84203" width="900">

---

### Client & Data Management

<img src="https://github.com/user-attachments/assets/1c5b6bd9-1c30-400b-aaa2-acd1730140d3" width="500">

<img src="https://github.com/user-attachments/assets/5b43affd-56ae-4759-848e-fac30c35e4be" width="500">

---

### Role & Permission Controls

<img src="https://github.com/user-attachments/assets/b728440d-f910-46f2-aab6-56d706771500" width="500">

<img src="https://github.com/user-attachments/assets/36d5851c-4e0a-4f14-a4d3-e9cd5ff6d1a0" width="500">

<img src="https://github.com/user-attachments/assets/4a72dc9c-056f-4595-bb9a-158241ce7b11" width="500">

<img src="https://github.com/user-attachments/assets/afe352d1-e574-41c2-8290-8ebc258d7bae" width="500">

---

### Full Interface Views

<img src="https://github.com/user-attachments/assets/a4763cb9-039d-47ed-9e30-a1c4d8f78ddd" width="900">

<img src="https://github.com/user-attachments/assets/ce89e189-38bd-4537-b968-c1b2594ac85e" width="900">

---

## 🛠 Tech Stack

### Frontend

* React (Vite) — high-performance single-page application
* Mantine UI — modern component system with glassmorphism design
* Framer Motion — smooth UI animations
* Axios — secure API communication with JWT interceptors

### Backend

* Django REST Framework — headless API architecture
* PostgreSQL — relational database for structured data integrity
* SimpleJWT — stateless authentication
* WhiteNoise — static file serving

---

## 🏗 System Architecture

Studio.OS uses a **decoupled architecture** separating frontend and backend responsibilities.

**Headless API**
The backend provides structured JSON data only, enabling future expansion into mobile or additional clients without rewriting business logic.

**State-Driven UI**
The frontend manages view states and filtering in real time while leveraging backend search and ordering filters.

**Data Siloing**
Database-level filtering ensures non-admin users can only access records assigned to their user ID.

---

## 🌟 Core Features

* Executive dashboard with revenue and activity tracking
* Permanent project records with locked identifiers
* Searchable client registry (CRM)
* Workflow lifecycle tracking (Pending → Active → Completed → Cancelled)
* Financial progress visualization
* Admin-controlled staff onboarding and role assignment

---

## 📦 Deployment

### Backend (Render)

Environment: Python 3.13.1

Build command:

```bash
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
```

Start command:

```bash
gunicorn core.wsgi:application --timeout 120
```

Database: Managed PostgreSQL instance

---

### Frontend (Vercel)

Framework: Vite

Build command:

```bash
npm run build
```

Environment variables:

```
VITE_API_URL=<Render backend URL>
```

---

## 🛠 Local Development Setup

### Clone Repository

```bash
git clone <repo-url>
```

---

### Backend Setup

```bash
cd interior_management
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## 📊 Key Business Logic Decisions

* Financial calculations use DecimalField for precise currency handling
* Custom user model supports role hierarchy (Admin vs Staff)
* JWT interceptors ensure seamless authenticated API communication

---

## 🎯 System Design Goals

* Operational clarity for small design teams
* Financial transparency across project lifecycle
* Secure role-based data access
* Scalable architecture ready for SaaS expansion

---

Developed for the Interior Design Industry.
