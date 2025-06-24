import requests
import pytz

BST = pytz.timezone("America/Chicago")

def get_or_create_product( access_token, location_id, product_name, custom_data):
        
        """
        First try to fetch existing product, if not found create a new one
        """
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Version': '2021-07-28'
        }
        
        # Search for existing product
        search_url = f"https://services.leadconnectorhq.com/products/?locationId={location_id}&search={product_name}"
        
        try:
            response = requests.get(search_url, headers=headers)
            if response.status_code == 200:
                products = response.json().get('products', [])
                if products:

                    # Return the first matching product ID

                    print("productsss: ", products)
                    return products[0].get('_id')
                
            else:
                 print("response error: ", response.text)
        except Exception as e:
            print(f"Error searching for product: {e}")
        
        # If no product found, create a new one
        return create_product(access_token, location_id, product_name, custom_data)
    
def create_product( access_token, location_id, product_name, custom_data):
        """
        Create a new product in GHL
        """
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        # Get price from custom data, default to 0 if not found
        price = custom_data.get("Price", "0")
        try:
            price_amount = float(price)
        except (ValueError, TypeError):
            price_amount = 0.0
        
        product_data = {
            "name": product_name,
            "locationId": location_id,
            "description": f"Auto-created product: {product_name}",
            "productType": "SERVICE",
            "availableInStore": True,
            "isTaxesEnabled": False,
            "isLabelEnabled": False,
            "slug": product_name.lower().replace(' ', '-').replace('_', '-')
        }
        
        url = "https://services.leadconnectorhq.com/products/"
        
        try:
            response = requests.post(url, headers=headers, json=product_data)
            if response.status_code in [200, 201]:
                product = response.json()
                print("product: ", product)
                return product.get('_id')
            else:
                print(f"Failed to create product: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error creating product: {e}")
            return None
    
def create_invoice( access_token, webhook_data, product_id, product_name):

        from datetime import datetime, timedelta
        """
        Create invoice in GHL
        """
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        location_id = webhook_data.get("locationId") or webhook_data.get("location", {}).get("id")
        
        # Get current date and due date (today + 2 days)
        current_date = datetime.now(BST)
        issue_date = current_date.strftime("%Y-%m-%d")
        due_date = (current_date + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Extract contact details from webhook
        contact_name = webhook_data.get("full_name", "")
        contact_email = webhook_data.get("email", "")
        contact_phone = webhook_data.get("phone", "")
        contact_id = webhook_data.get("contact_id", "")
        
        # Extract address details
        address1 = webhook_data.get("address1", "")
        city = webhook_data.get("city", "")
        state = webhook_data.get("state", "")
        country = webhook_data.get("country", "")
        
        # Get price from custom data or quote value
        custom_data = webhook_data.get("customData", {})
        price = custom_data.get("Price", webhook_data.get("Quote Value", "0"))
        try:
            amount = float(price) * 100  # Convert to cents for API
        except (ValueError, TypeError):
            amount = 0
        
        # Create invoice data
        business_name = webhook_data.get("company_name") or webhook_data.get("location", {}).get("name", "Business Name")
        
        # Create invoice data
        invoice_data = {
            "altId": location_id,
            "altType": "location",
            "name": f"{product_name} - {contact_name}",
            "currency": "USD",
            "businessDetails": {
                "name": business_name,
            },
            "items": [
                {
                    "name": product_name,
                    "description": f"Service: {product_name}",
                    "productId": product_id,
                    "currency": "USD",
                    "amount": int(amount),
                    "qty": 1,
                    "type": "one_time",
                    "taxInclusive": False
                }
            ],
            "discount": {
                "value": 0.00,
                "type": "percentage"
            },
            "title": "INVOICE",
            "contactDetails": {
                "id": contact_id,
                "name": contact_name,
                "phoneNo": contact_phone,
                "email": contact_email,
                "address": {
                    "addressLine1": address1,
                    "city": city,
                    "state": state,
                    "countryCode": country,
                    "postalCode": ""
                }
            },
            "issueDate": issue_date,
            "dueDate": due_date,
            "sentTo": {
                "email": [contact_email] if contact_email else []
            },
            "liveMode": True,
            "automaticTaxesEnabled": False,
            "invoiceNumberPrefix": "INV-"
        }
        
        # Remove empty email arrays to avoid API issues
        if not invoice_data["sentTo"]["email"]:
            del invoice_data["sentTo"]["email"]
        
        url = "https://services.leadconnectorhq.com/invoices/"
        
        try:
            response = requests.post(url, headers=headers, json=invoice_data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"Failed to create invoice: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error creating invoice: {e}")
            return None