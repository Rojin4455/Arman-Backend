import requests
import time
from typing import List, Dict, Any, Optional
from django.utils.dateparse import parse_datetime
from django.db import transaction
from data_management_app.models import Contact
from accounts.models import GHLAuthCredentials


def fetch_all_contacts(location_id: str, access_token: str = None) -> List[Dict[str, Any]]:
    """
    Fetch all contacts from GoHighLevel API with proper pagination handling.
    
    Args:
        location_id (str): The location ID for the subaccount
        access_token (str, optional): Bearer token for authentication
        
    Returns:
        List[Dict]: List of all contacts
    """

    if not access_token:
        access_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdXRoQ2xhc3MiOiJMb2NhdGlvbiIsImF1dGhDbGFzc0lkIjoiYjhxdm83Vm9vUDNKRDNkSVpVNDIiLCJzb3VyY2UiOiJJTlRFR1JBVElPTiIsInNvdXJjZUlkIjoiNjgzMWZjYTU0Y2Y5M2VjZjk5NDRmZmJhLW1iMmhpeXowIiwiY2hhbm5lbCI6Ik9BVVRIIiwicHJpbWFyeUF1dGhDbGFzc0lkIjoiYjhxdm83Vm9vUDNKRDNkSVpVNDIiLCJvYXV0aE1ldGEiOnsic2NvcGVzIjpbImNvbnRhY3RzLnJlYWRvbmx5IiwiY29udGFjdHMud3JpdGUiLCJvcHBvcnR1bml0aWVzLnJlYWRvbmx5Iiwib3Bwb3J0dW5pdGllcy53cml0ZSIsImxvY2F0aW9ucy9jdXN0b21GaWVsZHMucmVhZG9ubHkiLCJsb2NhdGlvbnMvY3VzdG9tVmFsdWVzLndyaXRlIiwibG9jYXRpb25zL2N1c3RvbVZhbHVlcy5yZWFkb25seSIsImxvY2F0aW9ucy9jdXN0b21GaWVsZHMud3JpdGUiXSwiY2xpZW50IjoiNjgzMWZjYTU0Y2Y5M2VjZjk5NDRmZmJhIiwidmVyc2lvbklkIjoiNjgzMWZjYTU0Y2Y5M2VjZjk5NDRmZmJhIiwiY2xpZW50S2V5IjoiNjgzMWZjYTU0Y2Y5M2VjZjk5NDRmZmJhLW1iMmhpeXowIn0sImlhdCI6MTc0OTcyMzM4Ni4yNTMsImV4cCI6MTc0OTgwOTc4Ni4yNTN9.oVTgX3nYZqejoADncgyh3pinL7bPZkH0iJKsij4YXfEVh2KsDK_jJ7_xr1eZLcC7Up7nM9WFcz0inj05gzfat7pGSNPe1ULSYkf9FBWE6AAW6HdY_etXYWb3pf5Gxo9ovAhy5fzcY-dm_YzswqnEBQiYTNL8Wr4eECHEHJYvvQwVNv8jzTWzGE2FmPih1sdhRqLB0oEUtNBKQY2IH2Z5A8j3QGqH3ZH52xUolaSsrdsY7WjKPKs5EOqfOQuAtGYC35xNTHKeC-5bZIACEUhLg6GmO20k2vZOjaMJACDe-cnXAHEVYAfmESvMwEQdjEjupTQ1L0fs0D85_DVUWMhbAnQGJdtFGJL05zeqtNdLHpXHl678pIwYnXCBS9QM8NjGZwSG5NgnVglaYHEaqj8LFAMWHHYX1AW-KUcOZgp8J_zwZrDZ5sTuFMWZbAjCnVdsjWfq5eVb7aeSqbkMXWnJDe0R7zbdhM1H5kucfohzN9iKyJouibJJzWUYWGYDFiQ02wxcKxWOlpYNctSprr-cSxVbAIfonkxnOrfX6c-LXeZ2j4NpHfHKyKZ0WooFAYAtT-D1r7taX0MSAfKC-A_345sQAI-aDA0cppzv9N7_kp-nY5OVh5u2lI-MqejN7lstaZUOdBz5Dioy7qLW-G5k4lSpKzriharuR17D0sk5OnA"
    
    
    
    base_url = "https://services.leadconnectorhq.com/contacts/"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Version": "2021-07-28"
    }
    
    all_contacts = []
    start_after = None
    start_after_id = None
    page_count = 0
    
    while True:
        page_count += 1
        print(f"Fetching page {page_count}...")
        
        # Set up parameters for current request
        params = {
            "locationId": location_id,
            "limit": 100,  # Maximum allowed by API
        }
        
        # Add pagination parameters if available
        if start_after:
            params["startAfter"] = start_after
        if start_after_id:
            params["startAfterId"] = start_after_id
            
        try:
            response = requests.get(base_url, headers=headers, params=params)
            
            if response.status_code != 200:
                print(f"Error Response: {response.status_code}")
                print(f"Error Details: {response.text}")
                raise Exception(f"API Error: {response.status_code}, {response.text}")
            
            data = response.json()
            
            # Get contacts from response
            contacts = data.get("contacts", [])
            if not contacts:
                print("No more contacts found.")
                break
                
            all_contacts.extend(contacts)
            print(f"Retrieved {len(contacts)} contacts. Total so far: {len(all_contacts)}")
            
            # Check if there are more pages
            # GoHighLevel API uses cursor-based pagination
            meta = data.get("meta", {})
            
            # Update pagination cursors for next request
            if contacts:  # If we got contacts, prepare for next page
                last_contact = contacts[-1]
                
                # Get the ID for startAfterId (this should be a string)
                if "id" in last_contact:
                    start_after_id = last_contact["id"]
                
                # Get timestamp for startAfter (this must be a number/timestamp)
                start_after = None
                if "dateAdded" in last_contact:
                    # Convert to timestamp if it's a string
                    date_added = last_contact["dateAdded"]
                    if isinstance(date_added, str):
                        try:
                            from datetime import datetime
                            # Try parsing ISO format
                            dt = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
                            start_after = int(dt.timestamp() * 1000)  # Convert to milliseconds
                        except:
                            # Try parsing as timestamp
                            try:
                                start_after = int(float(date_added))
                            except:
                                pass
                    elif isinstance(date_added, (int, float)):
                        start_after = int(date_added)
                        
                elif "createdAt" in last_contact:
                    created_at = last_contact["createdAt"]
                    if isinstance(created_at, str):
                        try:
                            from datetime import datetime
                            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            start_after = int(dt.timestamp() * 1000)
                        except:
                            try:
                                start_after = int(float(created_at))
                            except:
                                pass
                    elif isinstance(created_at, (int, float)):
                        start_after = int(created_at)
            
            # Check if we've reached the end
            total_count = meta.get("total", 0)
            if total_count > 0 and len(all_contacts) >= total_count:
                print(f"Retrieved all {total_count} contacts.")
                break
                
            # If we got fewer contacts than the limit, we're likely at the end
            if len(contacts) < 100:
                print("Retrieved fewer contacts than limit, likely at end.")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            raise
            
        # Add a small delay to be respectful to the API
        time.sleep(0.1)
        
        # Safety check to prevent infinite loops
        if page_count > 1000:  # Adjust based on expected contact count
            print("Warning: Stopped after 1000 pages to prevent infinite loop")
            break
    
    print(f"\nTotal contacts retrieved: {len(all_contacts)}")

    sync_contacts_to_db(all_contacts)
    # return all_contacts




def sync_contacts_to_db(contact_data):
    """
    Syncs contact data from API into the local Contact model using bulk upsert.
    
    Args:
        contact_data (list): List of contact dicts from GoHighLevel API
    """
    contacts_to_create = []
    existing_ids = set(Contact.objects.filter(contact_id__in=[c['id'] for c in contact_data]).values_list('contact_id', flat=True))

    for item in contact_data:
        
        
        
        date_added = parse_datetime(item.get("dateAdded")) if item.get("dateAdded") else None
        

        contact_obj = Contact(
            contact_id=item.get("id"),
            first_name=item.get("firstName"),
            last_name=item.get("lastName"),
            phone=item.get("phone"),
            email=item.get("email"),
            dnd=item.get("dnd", False),
            country=item.get("country"),
            date_added=date_added,
            tags=item.get("tags", []),
            custom_fields=item.get("customFields", []),
            location_id=item.get("locationId"),
            timestamp=date_added
        )

        if item.get("id") in existing_ids:
            # Update existing contact
            Contact.objects.filter(contact_id=item["id"]).update(
                first_name=contact_obj.first_name,
                last_name=contact_obj.last_name,
                phone=contact_obj.phone,
                email=contact_obj.email,
                dnd=contact_obj.dnd,
                country=contact_obj.country,
                date_added=contact_obj.date_added,
                tags=contact_obj.tags,
                custom_fields=contact_obj.custom_fields,
                location_id=contact_obj.location_id,
                timestamp=contact_obj.timestamp
            )
        else:
            contacts_to_create.append(contact_obj)

    if contacts_to_create:
        with transaction.atomic():
            Contact.objects.bulk_create(contacts_to_create, ignore_conflicts=True)

    print(f"{len(contacts_to_create)} new contacts created.")
    print(f"{len(existing_ids)} existing contacts updated.")



