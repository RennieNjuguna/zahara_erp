import json
import logging
import requests
from django.utils import timezone
from .models import Invoice, ETIMSSettings

logger = logging.getLogger(__name__)

class ETIMSService:
    def __init__(self):
        self.settings = ETIMSSettings.objects.filter(is_active=True).first()

    def is_configured(self):
        return self.settings is not None and self.settings.kra_pin and self.settings.api_base_url

    def build_invoice_payload(self, invoice):
        """
        Builds the JSON payload for KRA eTIMS System-to-System integration.
        This is a typical structure. It might need adjustment based on the exact
        eTIMS API documentation provided by the user.
        """
        if not self.settings:
            raise Exception("eTIMS is not configured.")

        order = invoice.order
        customer = order.customer
        
        # Calculate totals
        total_taxable_amount = 0
        total_tax_amount = 0
        total_amount = 0
        
        item_list = []
        for index, item in enumerate(order.items.all(), start=1):
            product = item.product
            tax_code = product.tax_code or 'C' # Default to C (Export)
            
            # Tax rates mappings based on tax_code
            tax_rate_mapping = {
                'A': 0.16,
                'B': 0.08,
                'C': 0.00,
                'D': 0.00,
                'E': 0.08,
            }
            tax_rate = tax_rate_mapping.get(tax_code, 0)
            
            unit_price = float(item.price_per_stem)
            quantity = float(item.stems)
            item_total = float(item.total_amount)
            
            item_tax_amt = item_total * tax_rate
            
            total_taxable_amount += item_total
            total_tax_amount += item_tax_amt
            total_amount += (item_total + item_tax_amt)
            
            item_list.append({
                "itemSeq": index,
                "itemCd": product.item_classification_code or "10000000", # Default or specific HS code
                "itemNm": product.name,
                "pkgUnitCd": "BX", # Box
                "pkgQty": item.boxes,
                "qtyUnitCd": "U", # Units (Stems)
                "qty": quantity,
                "prc": unit_price,
                "splyAmt": item_total,
                "totDcAmt": 0,
                "taxblAmt": item_total,
                "taxTyCd": tax_code,
                "taxAmt": item_tax_amt,
                "totAmt": item_total + item_tax_amt
            })

        payload = {
            "trdInvcNo": invoice.invoice_code,
            "invcNo": invoice.invoice_code,
            "orgInvcNo": "",
            "custNm": customer.name,
            "custNo": customer.short_code, # Use short code or PIN if available
            "custPin": "", # Add customer PIN if captured in the future
            "prcptNm": customer.name,
            "salesTyCd": "N", # Normal sales
            "rcptTyCd": "S", # Sales receipt
            "pmtTyCd": "01", # Cash/Credit
            "salesDt": order.date.strftime("%Y%m%d"),
            "stockRlsDt": order.date.strftime("%Y%m%d"),
            "cnclReqDt": "",
            "cnclDt": "",
            "rfndRsnCd": "",
            "totItemCnt": len(item_list),
            "taxblAmtA": total_taxable_amount if any(i['taxTyCd'] == 'A' for i in item_list) else 0,
            "taxblAmtB": total_taxable_amount if any(i['taxTyCd'] == 'B' for i in item_list) else 0,
            "taxblAmtC": total_taxable_amount if any(i['taxTyCd'] == 'C' for i in item_list) else 0,
            "taxblAmtD": total_taxable_amount if any(i['taxTyCd'] == 'D' for i in item_list) else 0,
            "taxblAmtE": total_taxable_amount if any(i['taxTyCd'] == 'E' for i in item_list) else 0,
            "taxRateA": 16,
            "taxRateB": 8,
            "taxRateC": 0,
            "taxRateD": 0,
            "taxRateE": 8,
            "taxAmtA": sum(i['taxAmt'] for i in item_list if i['taxTyCd'] == 'A'),
            "taxAmtB": sum(i['taxAmt'] for i in item_list if i['taxTyCd'] == 'B'),
            "taxAmtC": sum(i['taxAmt'] for i in item_list if i['taxTyCd'] == 'C'),
            "taxAmtD": sum(i['taxAmt'] for i in item_list if i['taxTyCd'] == 'D'),
            "taxAmtE": sum(i['taxAmt'] for i in item_list if i['taxTyCd'] == 'E'),
            "totTaxblAmt": total_taxable_amount,
            "totTaxAmt": total_tax_amount,
            "totAmt": total_amount,
            "remark": order.remarks or "",
            "itemList": item_list
        }
        
        return payload

    def submit_invoice(self, invoice):
        """
        Submits the invoice to KRA eTIMS API.
        """
        if not self.is_configured():
            invoice.etims_status = 'failed'
            invoice.etims_error_message = "eTIMS is not configured."
            invoice.save()
            return False, "eTIMS is not configured."

        payload = self.build_invoice_payload(invoice)
        
        # NOTE: This is a stubbed API call until we get the actual API details from the user.
        headers = {
            "Content-Type": "application/json",
            "pin": self.settings.kra_pin,
            "branchId": self.settings.branch_id,
        }
        
        # Try to make the API call
        try:
            # url = f"{self.settings.api_base_url}/saveReq"
            # response = requests.post(url, json=payload, headers=headers)
            # data = response.json()
            
            # STUBBED RESPONSE (Success scenario)
            # Remove this once the real API URL and method are available.
            invoice.etims_status = 'submitted'
            invoice.etims_receipt_number = f"KRA-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            invoice.etims_internal_data = f"INT-{invoice.invoice_code}"
            invoice.etims_signature = "STUBBED_SIGNATURE_STRING"
            invoice.etims_qr_code_url = f"https://etims.kra.go.ke/verify?receipt={invoice.etims_receipt_number}"
            invoice.etims_error_message = ""
            invoice.save()
            
            return True, "Invoice successfully submitted to eTIMS."
            
        except Exception as e:
            logger.error(f"eTIMS API Error: {str(e)}")
            invoice.etims_status = 'failed'
            invoice.etims_error_message = str(e)
            invoice.save()
            return False, str(e)
