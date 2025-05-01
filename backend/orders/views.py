from django.http import JsonResponse
from customers.models import Branch

def load_branches(request):
    customer_id = request.GET.get('customer_id')
    branches = Branch.objects.filter(customer_id=customer_id).values('id', 'name')
    return JsonResponse(list(branches), safe=False)

def get_branches(request):
    customer_id = request.GET.get('customer_id')
    branches = Branch.objects.filter(customer_id=customer_id)
    data = [{"id": b.id, "name": b.name} for b in branches]
    return JsonResponse(data, safe=False)
