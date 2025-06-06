import requests

from accounts.models import GHLAuthCredentials


def update_contact(contact_id, data):
    url = f'https://services.leadconnectorhq.com/contacts/{contact_id}'
    credentials = GHLAuthCredentials.objects.first()

    headers = {
        'Authorization': f'Bearer {credentials.access_token}',
        'Content-Type': 'application/json',
        'Version':'2021-07-28'
    }

    try:
        response = requests.put(url, headers=headers, json=data)
        return response.json()
    except Exception as e:
        return {'error':'Error while updating ghl contact'}