# Chit Fund Management System

A web-based chit fund management system built with FastAPI where 10 users participate in a 10-month scheme. Each user pays monthly installments, and one user receives the monthly payment each month (assigned by admin).

## Features

### User Features
- **Dashboard**: View all 10 months with installment and payment amounts
- **Payment Tracking**: Mark installments as paid (pending admin verification)
- **Month Assignment**: See which month you "took" (received payment)
- **Privacy**: Cannot see other users' names who took payments

### Admin Features
- **User Management**: Create and manage user accounts
- **Month Assignment**: Assign which user receives which month's payment
- **Payment Verification**: Verify user-marked payments
- **Complete Overview**: View all users, months, assignments, and payments
- **Statistics Dashboard**: See fund statistics and status

## Technology Stack

- **Backend**: FastAPI
- **Database**: SQLite with SQLAlchemy ORM
- **Authentication**: JWT tokens with bcrypt password hashing
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Templates**: Jinja2

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/satux14/fundmgr.git
   cd fundmgr
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Seed initial data**
   ```bash
   python seed_data.py
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the application**
   - Open browser and go to: `http://localhost:8000`
   - Default admin login:
     - Username: `admin`
     - Password: `admin123`

## Project Structure

```
fundmgr/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── database.py             # Database connection & session
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── auth.py                 # Authentication utilities
│   ├── dependencies.py         # FastAPI dependencies
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # Login/logout endpoints
│   │   ├── users.py            # User dashboard endpoints
│   │   ├── admin.py            # Admin management endpoints
│   │   └── payments.py         # Payment tracking endpoints
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── user_dashboard.html
│   ├── admin_dashboard.html
│   ├── admin_users.html
│   ├── admin_months.html
│   └── admin_payments.html
├── data/                       # SQLite database directory
├── requirements.txt
├── seed_data.py               # Initial data seeding script
├── README.md
└── .gitignore
```

## Database Schema

### Users Table
- `id` (Primary Key)
- `username` (Unique)
- `password_hash` (bcrypt)
- `full_name`
- `role` (user/admin)
- `created_at`

### Months Table
- `id` (Primary Key)
- `month_name` (Jan, Feb, etc.)
- `month_number` (1-10)
- `installment_amount` (decimal)
- `payment_amount` (decimal)
- `year` (2026)

### UserMonthAssignments Table
- `id` (Primary Key)
- `user_id` (Foreign Key → Users)
- `month_id` (Foreign Key → Months, Unique)
- `assigned_at` (timestamp)
- `assigned_by` (admin user_id)

### InstallmentPayments Table
- `id` (Primary Key)
- `user_id` (Foreign Key → Users)
- `month_id` (Foreign Key → Months)
- `paid_at` (timestamp)
- `marked_by` (user_id who marked it)
- `verified_by` (admin user_id, nullable)
- `status` (pending/verified)

## API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User login
- `GET /logout` - User logout
- `GET /auth/me` - Get current user info

### User Endpoints
- `GET /dashboard` - User dashboard view
- `GET /api/user/months` - Get all months with user's data
- `POST /api/user/payments` - Mark installment as paid

### Admin Endpoints
- `GET /admin/dashboard` - Admin dashboard
- `GET /admin/users` - List all users
- `POST /admin/users` - Create new user
- `GET /admin/months` - View all months and assignments
- `POST /admin/assign-month` - Assign month to user
- `GET /admin/payments` - View all payments
- `POST /admin/payments/verify` - Verify a payment

## Usage

1. **Login** with admin credentials
2. **Create Users** from the Admin → Users menu
3. **Assign Months** to users from Admin → Months menu
4. **Users can mark payments** from their dashboard
5. **Admin verifies payments** from Admin → Payments menu

## Security Notes

- Change default admin password immediately
- Use strong SECRET_KEY in production (update in `app/auth.py`)
- Ensure proper file permissions on data directory
- Regularly backup database files

## License

Proprietary - All rights reserved

