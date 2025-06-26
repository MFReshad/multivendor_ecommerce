# 🛒 Multivendor E-Commerce Platform (Django + DRF)

A full-featured multivendor e-commerce backend built with **Django** and **Django REST Framework**, supporting buyers, sellers, and admins. It includes user registration, product management, cart, orders, reviews, payments (Stripe-ready), and admin approval workflows.

---

## 🚀 Features

- 🔐 JWT authentication (SimpleJWT)
- 👥 Role-based access: buyer, seller, admin
- 🏬 Seller registration + approval
- 🛍️ Products, categories, variants, reviews
- 🛒 Cart and wishlist
- 📦 Order creation and tracking
- 💳 Stripe-ready payment model
- 📈 Stats for admin/seller dashboard
- 🌐 Swagger + Redoc auto-generated API docs

---

## 🛠️ Technologies Used

- Django 5.2.3
- Django REST Framework
- Simple JWT
- drf-yasg (Swagger UI)
- django-filter
- Pillow (Image support)
- Stripe (integration-ready)
- SQLite (default, can be replaced)

---

## 📂 Project Structure
```bash
multivendor_ecommerce/
├── apps/
│ ├── users/ # Custom User model & authentication
│ ├── products/ # Product management
│ ├── cart/ # Cart & wishlist logic
│ ├── orders/ # Orders & items
│ ├── payments/ # Payment models
├── media/ # Product images
├── requirements.txt
├── README.md
└── manage.py
```



---

## ✅ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/mfreshad/multivendor-ecommerce.git
cd multivendor-ecommerce
```

### 2. Create & Activate Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate (Windows)
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser (Admin)
```bash
python manage.py createsuperuser
```

### 6. Run the Server
```bash
python manage.py runserver
```

Visit:

Swagger: http://localhost:8000/swagger/

Redoc: http://localhost:8000/redoc/


---


## 🔐 Authentication

Register: POST /api/users/register/

Login: POST /api/users/login/

Token refresh: POST /api/token/refresh/

---
## 🔍 API Modules Overview

| Module   | Description                                                       |
| -------- | ----------------------------------------------------------------- |
| Users    | Register/login/profile/admin approval                             |
| Products | List/create/update/delete products, categories, reviews, variants |
| Cart     | Add/remove/update cart items & wishlist                           |
| Orders   | Place/manage orders per user/seller                               |
| Payments | Create/manage payments & status updates                           |
