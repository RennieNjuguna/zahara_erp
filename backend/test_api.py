#!/usr/bin/env python
"""
Simple test script to verify API endpoints are accessible.
Run this from the backend directory: python test_api.py
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zahara_backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status

def test_api_endpoints():
    """Test basic API endpoint accessibility"""

    print("Testing Zahara ERP API Endpoints...")
    print("=" * 50)

    # Create test user if it doesn't exist
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com', 'is_staff': True}
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print("✓ Created test user")
    else:
        print("✓ Test user already exists")

    # Initialize API client
    client = APIClient()

    # Test JWT authentication
    print("\n1. Testing JWT Authentication...")
    auth_response = client.post('/api/v1/auth/token/', {
        'username': 'testuser',
        'password': 'testpass123'
    })

    if auth_response.status_code == status.HTTP_200_OK:
        token = auth_response.data['access']
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        print("✓ JWT authentication successful")
    else:
        print(f"✗ JWT authentication failed: {auth_response.status_code}")
        return

    # Test API endpoints
    endpoints = [
        ('/api/v1/customers/', 'Customers'),
        ('/api/v1/products/', 'Products'),
        ('/api/v1/orders/', 'Orders'),
        ('/api/v1/payments/', 'Payments'),
        ('/api/v1/expenses/', 'Expenses'),
        ('/api/v1/employees/', 'Employees'),
        ('/api/v1/analytics/dashboard/', 'Dashboard Analytics'),
    ]

    print("\n2. Testing API Endpoints...")
    for endpoint, name in endpoints:
        try:
            response = client.get(endpoint)
            if response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
                print(f"✓ {name}: {response.status_code}")
            else:
                print(f"✗ {name}: {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: Error - {str(e)}")

    print("\n3. Testing API Browser Interface...")
    browser_client = Client()
    try:
        response = browser_client.get('/api/v1/')
        if response.status_code == status.HTTP_200_OK:
            print("✓ API browser interface accessible")
        else:
            print(f"✗ API browser interface: {response.status_code}")
    except Exception as e:
        print(f"✗ API browser interface: Error - {str(e)}")

    print("\n" + "=" * 50)
    print("API Testing Complete!")
    print("\nTo access the API:")
    print("1. Start the server: python manage.py runserver")
    print("2. Visit: http://localhost:8000/api/v1/")
    print("3. Use JWT token for authentication in API requests")

if __name__ == '__main__':
    test_api_endpoints()
