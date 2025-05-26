from django.shortcuts import render
from data_management_app.tasks import handle_webhook_event
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from data_management_app.models import WebhookLog
from data_management_app.tasks import handle_webhook_event
from rest_framework.generics import ListAPIView
from django.db.models import Q
from .models import Contact
from .serializers import ContactSerializer
from .pagination import ContactPagination



@csrf_exempt
def webhook_handler(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        print("date:----- ", data)
        WebhookLog.objects.create(data=data)
        event_type = data.get("type")
        handle_webhook_event.delay(data, event_type)
        return JsonResponse({"message":"Webhook received"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    


class ContactSearchView(ListAPIView):
    serializer_class = ContactSerializer
    pagination_class = ContactPagination

    def get_queryset(self):
        query = self.request.query_params.get('search', '')
        if query:
            return Contact.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query) |
                Q(country__icontains=query)
            ).order_by('-date_added')
        return Contact.objects.all().order_by('-date_added')
