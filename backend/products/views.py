from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Count, Avg, Min, Max
from django.core.paginator import Paginator
from .models import Product, CustomerProductPrice
from customers.models import Customer


def product_list(request):
    """Display list of all products with search and pagination"""
    search_query = request.GET.get('search', '')
    min_stem_length = request.GET.get('min_stem_length', '')
    max_stem_length = request.GET.get('max_stem_length', '')
    
    products = Product.objects.all().order_by('name')
    
    # Apply search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
        )
    
    # Apply stem length filters
    if min_stem_length:
        products = products.filter(stem_length_cm__gte=int(min_stem_length))
    if max_stem_length:
        products = products.filter(stem_length_cm__lte=int(max_stem_length))
    
    # Annotate with price statistics
    products = products.annotate(
        total_customers=Count('customer_prices', distinct=True),
        avg_price=Avg('customer_prices__price_per_stem')
    )
    
    # Pagination
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'min_stem_length': min_stem_length,
        'max_stem_length': max_stem_length,
        'total_products': products.count(),
    }
    return render(request, 'products/product_list.html', context)


def product_detail(request, product_id):
    """Display detailed information about a specific product"""
    product = get_object_or_404(Product, id=product_id)
    
    # Get customer prices for this product
    customer_prices = CustomerProductPrice.objects.filter(product=product).select_related('customer')
    
    # Get price statistics
    if customer_prices.exists():
        min_price = customer_prices.aggregate(min_price=Min('price_per_stem'))['min_price']
        max_price = customer_prices.aggregate(max_price=Max('price_per_stem'))['max_price']
        avg_price = customer_prices.aggregate(avg_price=Avg('price_per_stem'))['avg_price']
    else:
        min_price = max_price = avg_price = None
    
    # Get customers who have prices for this product
    customers_with_prices = Customer.objects.filter(product_prices__product=product).distinct()
    
    # Get customers without prices for this product
    customers_without_prices = Customer.objects.exclude(product_prices__product=product)
    
    context = {
        'product': product,
        'customer_prices': customer_prices,
        'min_price': min_price,
        'max_price': max_price,
        'avg_price': avg_price,
        'customers_with_prices': customers_with_prices,
        'customers_without_prices': customers_without_prices,
        'total_customers': customers_with_prices.count(),
    }
    return render(request, 'products/product_detail.html', context)


def product_create(request):
    """Create a new product"""
    if request.method == 'POST':
        name = request.POST.get('name')
        stem_length_cm = request.POST.get('stem_length_cm')
        
        if name and stem_length_cm:
            try:
                stem_length_cm = int(stem_length_cm)
                if stem_length_cm <= 0:
                    messages.error(request, 'Stem length must be a positive number.')
                else:
                    product = Product.objects.create(
                        name=name,
                        stem_length_cm=stem_length_cm
                    )
                    messages.success(request, f'Product "{product.name}" created successfully!')
                    return redirect('products:product_detail', product_id=product.id)
            except ValueError:
                messages.error(request, 'Stem length must be a valid number.')
            except Exception as e:
                messages.error(request, f'Error creating product: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')
    
    context = {}
    return render(request, 'products/product_form.html', context)


def product_edit(request, product_id):
    """Edit an existing product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        stem_length_cm = request.POST.get('stem_length_cm')
        
        if name and stem_length_cm:
            try:
                stem_length_cm = int(stem_length_cm)
                if stem_length_cm <= 0:
                    messages.error(request, 'Stem length must be a positive number.')
                else:
                    product.name = name
                    product.stem_length_cm = stem_length_cm
                    product.save()
                    messages.success(request, f'Product "{product.name}" updated successfully!')
                    return redirect('products:product_detail', product_id=product.id)
            except ValueError:
                messages.error(request, 'Stem length must be a valid number.')
            except Exception as e:
                messages.error(request, f'Error updating product: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')
    
    context = {
        'product': product,
    }
    return render(request, 'products/product_form.html', context)


def product_delete(request, product_id):
    """Delete a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            product_name = product.name
            product.delete()
            messages.success(request, f'Product "{product_name}" deleted successfully!')
            return redirect('products:product_list')
        except Exception as e:
            messages.error(request, f'Error deleting product: {str(e)}')
    
    context = {
        'product': product,
    }
    return render(request, 'products/product_confirm_delete.html', context)


def price_create(request, product_id):
    """Create a new price for a product"""
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        stem_length_cm = request.POST.get('stem_length_cm')
        price_per_stem = request.POST.get('price_per_stem')
        
        if customer_id and stem_length_cm and price_per_stem:
            try:
                customer = Customer.objects.get(id=customer_id)
                stem_length_cm = int(stem_length_cm)
                price_per_stem = float(price_per_stem)
                
                if stem_length_cm <= 0:
                    messages.error(request, 'Stem length must be a positive number.')
                elif price_per_stem <= 0:
                    messages.error(request, 'Price must be a positive number.')
                else:
                    # Check if price already exists
                    existing_price = CustomerProductPrice.objects.filter(
                        customer=customer,
                        product=product,
                        stem_length_cm=stem_length_cm
                    ).first()
                    
                    if existing_price:
                        messages.error(request, f'Price already exists for {customer.name} at {stem_length_cm}cm stem length.')
                    else:
                        price = CustomerProductPrice.objects.create(
                            customer=customer,
                            product=product,
                            stem_length_cm=stem_length_cm,
                            price_per_stem=price_per_stem
                        )
                        messages.success(request, f'Price created successfully: {price.price_per_stem} per stem at {price.stem_length_cm}cm for {customer.name}')
                        return redirect('products:product_detail', product_id=product.id)
            except (ValueError, Customer.DoesNotExist) as e:
                messages.error(request, f'Invalid input: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error creating price: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')
    
    context = {
        'product': product,
        'customers': Customer.objects.all().order_by('name'),
    }
    return render(request, 'products/price_form.html', context)


def price_edit(request, price_id):
    """Edit an existing price"""
    price = get_object_or_404(CustomerProductPrice, id=price_id)
    
    if request.method == 'POST':
        stem_length_cm = request.POST.get('stem_length_cm')
        price_per_stem = request.POST.get('price_per_stem')
        
        if stem_length_cm and price_per_stem:
            try:
                stem_length_cm = int(stem_length_cm)
                price_per_stem = float(price_per_stem)
                
                if stem_length_cm <= 0:
                    messages.error(request, 'Stem length must be a positive number.')
                elif price_per_stem <= 0:
                    messages.error(request, 'Price must be a positive number.')
                else:
                    # Check if price already exists for different record
                    existing_price = CustomerProductPrice.objects.filter(
                        customer=price.customer,
                        product=price.product,
                        stem_length_cm=stem_length_cm
                    ).exclude(id=price.id).first()
                    
                    if existing_price:
                        messages.error(request, f'Price already exists for {price.customer.name} at {stem_length_cm}cm stem length.')
                    else:
                        price.stem_length_cm = stem_length_cm
                        price.price_per_stem = price_per_stem
                        price.save()
                        messages.success(request, f'Price updated successfully: {price.price_per_stem} per stem at {price.stem_length_cm}cm')
                        return redirect('products:product_detail', product_id=price.product.id)
            except ValueError as e:
                messages.error(request, f'Invalid input: {str(e)}')
            except Exception as e:
                messages.error(request, f'Error updating price: {str(e)}')
        else:
            messages.error(request, 'All fields are required.')
    
    context = {
        'price': price,
    }
    return render(request, 'products/price_form.html', context)


def price_delete(request, price_id):
    """Delete a price"""
    price = get_object_or_404(CustomerProductPrice, id=price_id)
    product_id = price.product.id
    
    if request.method == 'POST':
        try:
            price_info = f"{price.customer.name} - {price.price_per_stem} per stem at {price.stem_length_cm}cm"
            price.delete()
            messages.success(request, f'Price "{price_info}" deleted successfully!')
            return redirect('products:product_detail', product_id=product_id)
        except Exception as e:
            messages.error(request, f'Error deleting price: {str(e)}')
    
    context = {
        'price': price,
    }
    return render(request, 'products/price_confirm_delete.html', context)
