import requests
from celery import shared_task
from accounts.models import GHLAuthCredentials
from django.conf import settings
from accounts.utils import fetch_all_contacts


@shared_task
def make_api_for_ghl():
    
    credentials = GHLAuthCredentials.objects.first()
    
    print("credentials tokenL", credentials)
    refresh_token = credentials.refresh_token

    
    response = requests.post('https://services.leadconnectorhq.com/oauth/token', data={
        'grant_type': 'refresh_token',
        'client_id': settings.CLIENT_ID,
        'client_secret': settings.CLIENT_SECRET,
        'refresh_token': refresh_token
    })
    
    new_tokens = response.json()
    print("newtoken :", new_tokens)

    obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= new_tokens.get("locationId"),
            defaults={
                "access_token": new_tokens.get("access_token"),
                "refresh_token": new_tokens.get("refresh_token"),
                "expires_in": new_tokens.get("expires_in"),
                "scope": new_tokens.get("scope"),
                "user_type": new_tokens.get("userType"),
                "company_id": new_tokens.get("companyId"),
                "user_id":new_tokens.get("userId"),

            }
        )

@shared_task
def fetch_all_contacts_task(location_id, access_token):
    """
    Celery task to fetch all contacts for a given location using the provided access token.
    """
    fetch_all_contacts(location_id, access_token)

