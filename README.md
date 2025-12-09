# Zahara ERP - Agricultural Business Management System

## 🌱 Overview

Zahara ERP is a comprehensive Enterprise Resource Planning system designed specifically for agricultural businesses, with a focus on flower export operations. The system provides complete management of customers, orders, payments, invoicing, expenses, and agricultural planning.

## 🚀 Features

### ✅ Implemented Features

- **Customer Management**: Complete customer database with branches and preferences
- **Product Catalog**: Product management with customer-specific pricing
- **Order Processing**: Full order lifecycle from creation to delivery
- **Payment System**: Advanced payment processing with allocations and balance tracking
- **Invoice Generation**: Automated invoice creation and PDF generation
- **Expense Tracking**: Comprehensive expense management with categorization
- **Employee Management**: HR system for staff records and management
- **Agricultural Planning**: Crop and farm block management for planning
- **Analytics & Reporting**: Real-time dashboards and business intelligence
- **Multi-Currency Support**: KSH, USD, GBP, EUR currency support

### ⚠️ Under Construction

- **Credit Note System**: Credit note processing and management (in development)

## 🛠️ Technology Stack

- **Backend**: Django 3.2.18 + Django REST Framework 3.14.0
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: JWT tokens with Simple JWT
- **API**: RESTful API with 27 endpoints
- **Filtering**: Advanced querying with Django-filter
- **Permissions**: Role-based access control

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

   > **Note:** We use a new virtual environment `venv_new` and have adjusted dependencies for Python 3.7 compatibility.

   ```bash
   cd backend
   # Create new virtual environment
   python -m venv venv_new

   # Activate it
   # Windows:
   .\venv_new\Scripts\activate
   # Linux/Mac:
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
- **JWT Authentication**: http://localhost:8000/api/v1/auth/token/

## 📚 API Documentation

Complete API documentation is available in `ZAHARA_ERP_API_DOCUMENTATION.md` including:

- All 27 API endpoints
- Authentication setup
- Data models and types
- Testing instructions
- Production deployment guide

## 🔐 Authentication

The system uses JWT (JSON Web Token) authentication:

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

## 🧪 Testing

### Manual Testing

1. Visit the API browser at http://localhost:8000/api/v1/
2. Create a user account via Django admin
3. Test endpoints using the interactive interface

### API Testing

```bash
# Test API endpoints
cd backend
python -c "import requests; print(requests.get('http://localhost:8000/api/v1/').status_code)"
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

## 📊 System Architecture

```
Zahara ERP System
├── Backend (Django)
│   ├── API Layer (DRF)
│   ├── Business Logic
│   ├── Data Models
│   └── Authentication
├── Database (SQLite/PostgreSQL)
└── Frontend (Any framework can consume the API)
```

## 🔧 Development

### Project Structure

```
zahara_erp/
├── backend/                    # Django backend application
│   ├── api/                   # Django REST Framework API
│   │   ├── __init__.py
│   │   ├── filters.py         # API filtering classes
│   │   ├── permissions.py     # Custom permissions
│   │   ├── serializers.py     # Data serializers
│   │   ├── urls.py           # API URL routing
│   │   └── views.py          # API ViewSets
│   ├── customers/             # Customer management
│   │   ├── models.py         # Customer and Branch models
│   │   ├── views.py          # Customer views
│   │   ├── admin.py          # Admin interface
│   │   └── templates/        # Customer templates
│   ├── orders/               # Order processing
│   │   ├── models.py         # Order and OrderItem models
│   │   ├── views.py          # Order views
│   │   ├── forms.py          # Order forms
│   │   └── management/       # Management commands
│   ├── payments/             # Payment system
│   │   ├── models.py         # Payment and allocation models
│   │   ├── views.py          # Payment views
│   │   └── templates/        # Payment templates
│   ├── invoices/             # Invoice management
│   │   ├── models.py         # Invoice and CreditNote models
│   │   ├── views.py          # Invoice views
│   │   ├── forms.py          # Invoice forms
│   │   └── templates/        # Invoice templates
│   ├── expenses/             # Expense tracking
│   │   ├── models.py         # Expense models
│   │   ├── views.py          # Expense views
│   │   └── management/       # Management commands
│   ├── employees/            # HR management
│   │   ├── models.py         # Employee models
│   │   ├── views.py          # Employee views
│   │   └── templates/        # Employee templates
│   ├── products/             # Product catalog
│   │   ├── models.py         # Product and pricing models
│   │   ├── views.py          # Product views
│   │   └── templates/        # Product templates
│   ├── planting_schedule/    # Agricultural planning
│   │   ├── models.py         # Crop and FarmBlock models
│   │   ├── views.py          # Agricultural views
│   │   └── templates/        # Agricultural templates
│   ├── zahara_backend/       # Django project settings
│   │   ├── settings.py       # Project configuration
│   │   ├── urls.py          # Main URL routing
│   │   └── wsgi.py          # WSGI configuration
│   ├── templates/            # Global Django templates
│   ├── static/              # Static files (CSS, JS, images)
│   ├── staticfiles/         # Collected static files
│   ├── media/               # User uploaded files
│   │   ├── invoices_pdfs/   # Generated invoice PDFs
│   │   ├── expense_attachments/ # Expense receipts
│   │   └── account_statements_pdfs/ # Account statements
│   ├── manage.py            # Django management script
│   ├── requirements.txt     # Python dependencies
│   ├── urls.py             # Root URL configuration
│   └── db.sqlite3          # SQLite database
├── venv/                    # Python virtual environment
├── README.md               # Project documentation
├── ZAHARA_ERP_API_DOCUMENTATION.md # Complete API docs
└── Zahara_ERP_Documentation.zip # Archived documentation
```

### Key Modules

- **Customer Management**: Customer database, branches, preferences
- **Order Processing**: Orders, order items, customer defaults
- **Payment System**: Payments, allocations, customer balances
- **Invoice Management**: Invoices, credit notes (under construction)
- **Expense Tracking**: Expenses, categories, attachments
- **Agricultural Planning**: Crops, farm blocks, scheduling

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

## 🎯 Roadmap

- [ ] Complete credit note system implementation
- [ ] Add more advanced analytics and reporting
- [ ] Implement inventory management
- [ ] Add mobile app support
- [ ] Enhance agricultural planning features

---

**Zahara ERP - Growing Your Agricultural Business** 🌱
