import json
import urllib.request
from decimal import Decimal
from django.conf import settings
from .models import ExchangeRate

# Using a free API (open.er-api.com)
# Base currency KSH (KES)
API_URL = "https://open.er-api.com/v6/latest/KES"

def fetch_and_update_rates():
    """
    Fetches live exchange rates relative to KES (Kenyan Shilling)
    and updates the ExchangeRate model.
    """
    try:
        with urllib.request.urlopen(API_URL) as response:
            data = json.loads(response.read().decode())
            
        if data.get('result') != 'success':
            return False, "Failed to fetch rates from API"
            
        rates = data.get('rates', {})
        
        # Currencies we care about (add more as needed)
        target_currencies = ['USD', 'GBP', 'EUR']
        
        updated_count = 0
        for code in target_currencies:
            rate_in_kes = rates.get(code) # This is 1 KES = X USD
             
            if rate_in_kes:
                # We store "How much KSH is 1 Unit of Foreign Currency"
                # So if 1 KES = 0.0077 USD, then 1 USD = 1/0.0077 KES
                rate_decimal = Decimal(1) / Decimal(str(rate_in_kes))
                
                obj, created = ExchangeRate.objects.update_or_create(
                    currency=code,
                    defaults={'rate': rate_decimal}
                )
                updated_count += 1
                
        return True, f"Successfully updated {updated_count} currencies"
        
    except Exception as e:
        return False, str(e)
