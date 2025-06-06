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
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db import transaction
from django.shortcuts import get_object_or_404
from .models import Service, GlobalSettings, Purchase
from .serializers import ServiceSerializer
from .serializers import PurchaseCreateSerializer, GlobalSettingsSerializer, PurchaseDetailSerializer
from rest_framework.views import APIView




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








class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.prefetch_related(
        'features',
        'pricing_options__selected_features__feature',
        'questions__options'
    ).all()
    serializer_class = ServiceSerializer

    def create(self, request, *args, **kwargs):
        """
        Create a new service with nested data
        """
        # Handle both single service and services array
        data = request.data
        if 'services' in data:
            # Handle array of services
            services_data = data['services']
            minimum_price = data.get('minimumPrice', 0)
            
            created_services = []
            for service_data in services_data:
                service_data['minimumPrice'] = minimum_price
                serializer = self.get_serializer(data=service_data)
                serializer.is_valid(raise_exception=True)
                service = serializer.save()
                created_services.append(service)
            
            # Return all created services
            response_serializer = self.get_serializer(created_services, many=True)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            # Handle single service
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            service = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Update an existing service
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        print(service)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Delete a service and all related data
        """
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'])
    def toggle_active(self, request, pk=None):
        """
        Toggle service active status
        """
        service = self.get_object()
        service.is_active = not service.is_active
        service.save()
        serializer = self.get_serializer(service)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get only active services
        """
        active_services = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(active_services, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplicate a service with all its related data
        """
        original_service = self.get_object()
        serializer = self.get_serializer(original_service)
        data = serializer.data
        
        # Modify name to indicate it's a copy
        data['name'] = f"{data['name']} (Copy)"
        
        # Remove read-only fields
        data.pop('id', None)
        data.pop('created_at', None)
        data.pop('updated_at', None)
        
        # Create new service
        new_serializer = self.get_serializer(data=data)
        new_serializer.is_valid(raise_exception=True)
        new_service = new_serializer.save()
        
        return Response(new_serializer.data, status=status.HTTP_201_CREATED)





class CreatePurchaseView(APIView):
    def post(self, request):
        print('data structure in create purchase view====',request.data)
        serializer = PurchaseCreateSerializer(data=request.data)
        if serializer.is_valid():
            purchase = serializer.save()
            return Response({"message": "Purchase created successfully", "id": purchase.id}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ReviewView(APIView):
    def get(self, request, id):
        try:
            purchase = Purchase.objects.get(id=id)
            serializer = PurchaseDetailSerializer(purchase)
            return Response(serializer.data, status=200)
        except Purchase.DoesNotExist:
            return Response({'error':'not found'}, status=404)

    
class globalsettingsView(APIView):
    def get(self, request):
        global_settings = GlobalSettings.load()
        serializer = GlobalSettingsSerializer(global_settings)
        return Response(serializer.data)

    def post(self, request):
        global_settings = GlobalSettings.load()
        serializer = GlobalSettingsSerializer(global_settings, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
    