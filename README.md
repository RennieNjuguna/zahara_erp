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

2. **Install dependencies**
   ```bash
   cd backend
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
├── backend/
│   ├── api/                 # Django REST Framework API
│   ├── customers/           # Customer management
│   ├── orders/             # Order processing
│   ├── payments/           # Payment system
│   ├── invoices/           # Invoice management
│   ├── expenses/           # Expense tracking
│   ├── employees/          # HR management
│   ├── planting_schedule/  # Agricultural planning
│   └── zahara_backend/     # Django project settings
├── templates/              # Django templates
├── static/                 # Static files
├── media/                  # Media files
└── requirements.txt        # Python dependencies
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
