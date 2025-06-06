import requests

from accounts.models import GHLAuthCredentials


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