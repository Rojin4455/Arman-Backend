from celery import shared_task
from accounts.models import GHLAuthCredentials
from django.utils.dateparse import parse_datetime
from data_management_app.helpers import create_or_update_contact, delete_contact


@shared_task
def handle_webhook_event(data, event_type):
    try:
        if event_type in ["ContactCreate", "ContactUpdate"]:
            create_or_update_contact(data)
        elif event_type == "ContactDelete":
            delete_contact(data)
    except Exception as e:
        print(f"Error handling webhook event: {str(e)}")