from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Employee


def employee_list(request):
    """Display list of all employees with search and pagination"""
    search_query = request.GET.get('search', '')
    position_filter = request.GET.get('position', '')
    date_joined_filter = request.GET.get('date_joined', '')
    
    employees = Employee.objects.all().order_by('last_name', 'first_name')
    
    # Apply search filter
    if search_query:
        employees = employees.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(position__icontains=search_query)
        )
    
    # Apply position filter
    if position_filter:
        employees = employees.filter(position__icontains=position_filter)
    
    # Apply date joined filter
    if date_joined_filter:
        employees = employees.filter(date_joined__icontains=date_joined_filter)
    
    # Get unique positions for filter dropdown
    positions = Employee.objects.values_list('position', flat=True).distinct().order_by('position')
    
    # Pagination
    paginator = Paginator(employees, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'position_filter': position_filter,
        'date_joined_filter': date_joined_filter,
        'positions': positions,
        'total_employees': employees.count(),
    }
    return render(request, 'employees/employee_list.html', context)


def employee_detail(request, employee_id):
    """Display detailed information about a specific employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    # Calculate years of service
    from datetime import date
    today = date.today()
    years_of_service = today.year - employee.date_joined.year - ((today.month, today.day) < (employee.date_joined.month, employee.date_joined.day))
    
    context = {
        'employee': employee,
        'years_of_service': years_of_service,
    }
    return render(request, 'employees/employee_detail.html', context)


def employee_create(request):
    """Create a new employee"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        position = request.POST.get('position')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        date_joined = request.POST.get('date_joined')
        
        if first_name and last_name and position and email and date_joined:
            try:
                # Check if email already exists
                if Employee.objects.filter(email=email).exists():
                    messages.error(request, f'An employee with email "{email}" already exists.')
                else:
                    employee = Employee.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        position=position,
                        email=email,
                        phone_number=phone_number,
                        date_joined=date_joined
                    )
                    messages.success(request, f'Employee "{employee.first_name} {employee.last_name}" created successfully!')
                    return redirect('employees:employee_detail', employee_id=employee.id)
            except Exception as e:
                messages.error(request, f'Error creating employee: {str(e)}')
        else:
            messages.error(request, 'First name, last name, position, email, and date joined are required.')
    
    context = {}
    return render(request, 'employees/employee_form.html', context)


def employee_edit(request, employee_id):
    """Edit an existing employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        position = request.POST.get('position')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        date_joined = request.POST.get('date_joined')
        
        if first_name and last_name and position and email and date_joined:
            try:
                # Check if email already exists for different employee
                existing_email = Employee.objects.filter(email=email).exclude(id=employee.id).first()
                if existing_email:
                    messages.error(request, f'An employee with email "{email}" already exists.')
                else:
                    employee.first_name = first_name
                    employee.last_name = last_name
                    employee.position = position
                    employee.email = email
                    employee.phone_number = phone_number
                    employee.date_joined = date_joined
                    employee.save()
                    messages.success(request, f'Employee "{employee.first_name} {employee.last_name}" updated successfully!')
                    return redirect('employees:employee_detail', employee_id=employee.id)
            except Exception as e:
                messages.error(request, f'Error updating employee: {str(e)}')
        else:
            messages.error(request, 'First name, last name, position, email, and date joined are required.')
    
    context = {
        'employee': employee,
    }
    return render(request, 'employees/employee_form.html', context)


def employee_delete(request, employee_id):
    """Delete an employee"""
    employee = get_object_or_404(Employee, id=employee_id)
    
    if request.method == 'POST':
        try:
            employee_name = f"{employee.first_name} {employee.last_name}"
            employee.delete()
            messages.success(request, f'Employee "{employee_name}" deleted successfully!')
            return redirect('employees:employee_list')
        except Exception as e:
            messages.error(request, f'Error deleting employee: {str(e)}')
    
    context = {
        'employee': employee,
    }
    return render(request, 'employees/employee_confirm_delete.html', context)
