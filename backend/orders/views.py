from django.http import JsonResponse
from customers.models import Branch

def get_branches(request):
    customer_id = request.GET.get('customer')
    if customer_id:
        branches = Branch.objects.filter(customer_id=customer_id)
        return JsonResponse([{'id': b.id, 'name': b.name} for b in branches], safe=False)
    return JsonResponse([], safe=False)
