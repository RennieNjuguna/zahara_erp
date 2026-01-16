# Zahara ERP - Agricultural Business Management System

## 🌱 Overview

Zahara ERP is a comprehensive Enterprise Resource Planning system designed specifically for agricultural businesses, with a focus on flower export operations. The system provides complete management of customers, orders, payments, invoicing, expenses, and agricultural planning.

## 🚀 Features

### ✅ Core Modules

- **Customer Management**: Complete customer database with branches, currency preferences, and contact details.
- **Product Catalog**: Product management with customer-specific pricing and stem-length variations.
- **Order Processing**: Full order lifecycle from creation to delivery.
- **Payment System**: Advanced payment processing with allocations (Full/Partial) and real-time balance tracking.
- **Invoice Generation**: Automated invoice creation and **native PDF generation** (ReportLab) sent via email or downloadable.
- **Credit Note System**: Full credit note lifecycle supporting multi-order credits, wizard-based creation, and auto-approval workflows.
- **Expense Tracking**: Comprehensive expense management with categorization and attachment support.
- **Missed Sales Tracker**: Track lost opportunities, visualize trends, and estimate potential revenue loss (KES) with interactive analytics.
- **Agricultural Planning**: Crop and farm block management for production planning.

### 📊 Analytics & Dashboards

- **Main Dashboard**: Real-time overview of Sales, Payments, and Expenses.
  - **Multi-Currency Aggregation**: Automatically converts USD, EUR, GBP to KES for consolidated totals.
  - **Interactive Charts**: Monthly data visualization.
- **Missed Sales Analytics**: Monthly trends and top product breakdown charts.

### 🛡️ Security & Architecture

- **Authentication**: Global login requirement with role-based access control (RBAC).
- **Technology**: Django 3.2+ with Django REST Framework.
- **PDF Engine**: Python-native `reportlab` (No external OS dependencies like wkhtmltopdf).

## ⚠️ Under Construction

- **Inventory Management**: Stock level tracking.
- **Mobile App**: Dedicated mobile interface for field usage.

## 🛠️ Technology Stack

- **Backend**: Django 3.2.18 + Django REST Framework 3.14.0
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Frontend**: Django Templates + Bootstrap 5 + HTMX + Chart.js
- **PDF Generation**: ReportLab
- **Authentication**: Session & JWT
- **API**: RESTful API with comprehensive endpoints

## 📦 Installation

### Prerequisites

- Python 3.7+
- pip (Python package manager)

### Setup Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/rennydev/zahara-erp.git
   cd zahara-erp
   ```

2. **Setup Virtual Environment & Install Dependencies**

   > **Note:** We use a dedicated virtual environment `venv_new` for Python 3.7 compatibility.

   ```bash
   cd backend
   # Create new virtual environment
   python -m venv venv_new

   # Activate it (Windows)
   .\venv_new\Scripts\activate
   # Activate it (Linux/Mac)
   # source venv_new/bin/activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Run database migrations**

   ```bash
   python manage.py migrate
   ```

4. **Create superuser account**

   ```bash
   python manage.py createsuperuser
   ```

5. **Start development server**
   ```bash
   python manage.py runserver
   ```

## 🌐 Access Points

Once the server is running, you can access:

- **Main Application**: http://localhost:8000/
- **API Browser**: http://localhost:8000/api/v1/
- **Admin Panel**: http://localhost:8000/admin/

## 📚 API Documentation

Complete API documentation is available in `ZAHARA_ERP_API_DOCUMENTATION.md` including:

- All 27 API endpoints
- Authentication setup
- Data models and types
- Testing instructions

## 🔐 Authentication

The system supports both Session (Browser) and JWT (API) authentication.

**API Auth Example:**

```bash
# Get access token
POST /api/v1/auth/token/
{
  "username": "your_username",
  "password": "your_password"
}

# Use token in requests
GET /api/v1/customers/
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## 🚀 Production Deployment

### Database Configuration

Update `settings.py` for PostgreSQL:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'zahara_erp',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Environment Variables

Create a `.env` file:

```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@localhost/zahara_erp
```

### Production Commands

```bash
# Install production dependencies
pip install gunicorn whitenoise

# Collect static files
python manage.py collectstatic

# Start production server
gunicorn zahara_backend.wsgi:application
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**Renny Dev**

- GitHub: [@rennydev](https://github.com/rennydev)

## 📞 Support

For support and questions:

- Create an issue on GitHub
- Check the API documentation in `ZAHARA_ERP_API_DOCUMENTATION.md`
