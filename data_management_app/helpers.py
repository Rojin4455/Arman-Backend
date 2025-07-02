import requests
from accounts.models import GHLAuthCredentials
from accounts.utils import fetch_contacts_locations
from data_management_app.models import Contact

def create_or_update_contact(data):
    contact_id = data.get("id")
    contact, created = Contact.objects.update_or_create(
        contact_id=contact_id,
        defaults={
            "first_name": data.get("firstName"),
            "last_name": data.get("lastName"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "dnd": data.get("dnd", False),
            "country": data.get("country"),
            "date_added": data.get("dateAdded"),
            "location_id": data.get("locationId"),
        }
    )
    cred = GHLAuthCredentials.objects.first()
    fetch_contacts_locations([data], data.get("locationId"), data.get("locationId"), cred.access_token)
    print("Contact created/updated:", contact_id)

def delete_contact(data):
    contact_id = data.get("id")
    try:
        contact = Contact.objects.get(contact_id=contact_id)
        contact.delete()
        print("Contact deleted:", contact_id)
    except Contact.DoesNotExist:
        print("Contact not found for deletion:", contact_id)