import requests

from accounts.models import GHLAuthCredentials
from data_management_app.models import Contact


def update_contact(contact_id, data):
    url = f'https://services.leadconnectorhq.com/contacts/{contact_id}'
    credentials = GHLAuthCredentials.objects.first()
    print(credentials, 'creee')

    headers = {
        'Authorization': f'Bearer {credentials.access_token}',
        'Content-Type': 'application/json',
        'Version':'2021-07-28'
    }

    try:
        response = requests.put(url, headers=headers, json=data)
        print(response.json(), 'responseeeeee')
        return response.json()
    except Exception as e:
        print(e, 'errorrr')
        return {'error':'Error while updating ghl contact'}
    
def add_tags(contact_id):
    url = f'https://services.leadconnectorhq.com/contacts/{contact_id}'
    credentials = GHLAuthCredentials.objects.first()

    contact = Contact.objects.filter(contact_id=contact_id).first()
    tags = contact.tags or []
    if "Quote Accepted" not in tags:
        tags.append("Quote Accepted")


    headers = {
        'Authorization': f'Bearer {credentials.access_token}',
        'Content-Type': 'application/json',
        'Version': '2021-07-28'
    }

    payload = {
        "tags": tags
    }

    try:
        response = requests.put(url, headers=headers, json=payload)
        print(response.status_code, response.text)
        if response.status_code == 200:
            return response.json()
        else:
            return False
    except Exception as e:
        print("Error while adding tag:", e)
        return False

def add_custom_field(contact_id, access_token, data):
    url = f'https://services.leadconnectorhq.com/contacts/{contact_id}'
    credentials = GHLAuthCredentials.objects.first()
    print(credentials, 'creee')

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Version':'2021-07-28'
    }

    try:
        response = requests.put(url, headers=headers, json=data)
        print(response.json(), 'responseeeeee')
        return response.json()
    except Exception as e:
        print(e, 'errorrr')
        return {'error':'Error while updating ghl contact'}