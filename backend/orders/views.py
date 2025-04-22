from django.http import JsonResponse
from customers.models import Branch

def get_branches(request):
    customer_id = request.GET.get('customer_id')
    branches = []

    if customer_id:
        branches = Branch.objects.filter(customer_id=customer_id).values('id', 'name')

    return JsonResponse({'branches': list(branches)})
