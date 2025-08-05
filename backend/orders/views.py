from django.http import JsonResponse
from customers.models import Branch
from .models import Order

def get_branches(request):
    customer_id = request.GET.get('customer_id')
    if customer_id:
        branches = Branch.objects.filter(customer_id=customer_id)
        return JsonResponse([{'id': b.id, 'name': b.name} for b in branches], safe=False)
    return JsonResponse([], safe=False)

def get_orders(request):
    customer_id = request.GET.get('customer_id')
    if customer_id:
        orders = Order.objects.filter(customer_id=customer_id).order_by('-date')
        return JsonResponse([{
            'id': order.id,
            'invoice_code': order.invoice_code,
            'date': order.date.strftime('%Y-%m-%d'),
            'total_amount': str(order.total_amount)
        } for order in orders], safe=False)
    return JsonResponse([], safe=False)
