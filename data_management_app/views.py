from django.shortcuts import render
from data_management_app.tasks import handle_webhook_event
import json
from django.conf import settings
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
from .models import Service, GlobalSettings, Purchase, PurchasedService, Feature, PurChasedServiceFeature, PricingOptionFeature
from .serializers import ServiceSerializer
from .serializers import PurchaseCreateSerializer, GlobalSettingsSerializer, PurchaseDetailSerializer, FinalSubmissionSerializer
from rest_framework.views import APIView
from .utils import update_contact, add_tags, add_custom_field
from accounts.models import GHLAuthCredentials


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from data_management_app.services import get_or_create_product, create_invoice




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
        query = self.request.query_params.get('search', '').strip()
        qs = Contact.objects.all()

        if query:
            keywords = query.split()
            q_object = Q()
            for keyword in keywords:
                q_object |= Q(first_name__icontains=keyword)
                q_object |= Q(last_name__icontains=keyword)
                q_object |= Q(email__icontains=keyword)
                q_object |= Q(phone__icontains=keyword)
                q_object |= Q(country__icontains=keyword)
            qs = qs.filter(q_object)

        return qs.order_by('-date_added')








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
        contact_id=request.data.get('contact')
        serializer = PurchaseCreateSerializer(data=request.data)
        if serializer.is_valid():
            purchase = serializer.save()
            data = {"customFields": [
                {
                    "id": "Bff2eZtlr82uvVQmByPh", #custom field id
                    "field_value": f'{settings.FRONTEND_URL}/user/review/{purchase.id}/'
                }
            ]}
            res = update_contact(contact_id, data)
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
    
class FinalSubmition(APIView):
    def post(self, request, quoteId):
        purchase_id = request.data.get('purchase_id')
        purchase=Purchase.objects.get(id=purchase_id)
        contact_id = purchase.contact.contact_id
        serializer = FinalSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            purchase = Purchase.objects.get(id=data['purchase_id'])

            # Update purchase
            purchase.is_submited = True
            purchase.signature = data['signature']
            purchase.total_amount = data['total_amount']
            purchase.save()

            # Update each PurchasedServicePlan
            for service_data in data['services']:
                try:
                    purchased_plan = PurchasedService.objects.get(
                        id=service_data['service_id']
                    )
                    price_plan = service_data['price_plan']
                    purchased_plan.selected_plan = price_plan
                    purchased_plan.save()

                    #add plan_name as a tag in ghl contact
                    add_tags(contact_id, plan_name=price_plan.name)
                    
                except PurchasedService.DoesNotExist:
                    return Response(
                        {"detail": f"PurchasedServicePlan for service {service_data['service_id']} not found"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            if add_tags(contact_id):
                data = {"customFields": [
                    {
                        "id": "AfQbphMXdk6rk6vnWPPU", #custom field id
                        "field_value": float(purchase.total_amount)
                    }
                ]}
                res = update_contact(contact_id, data)
                return Response({"detail": "Submission completed successfully."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class validate_locationId(APIView):
    def get(self, request):
        location_id = request.data.get('location_id')
        if not location_id:
            return Response({'error':'locationId not found'}, status=401)
        
        credentials = GHLAuthCredentials.objects.first()
        
        if location_id != credentials.location_id:
            return Response({'error':'Unauthenticated locationId'}, status=401)
        
        return Response({'status':True},status=200)
    



@method_decorator(csrf_exempt, name='dispatch')
class GhlWebhookView(View):
    def post(self, request):
        try:
            webhook_data = json.loads(request.body)
            
            # Get location ID from webhook data
            location_id = webhook_data.get("locationId") or webhook_data.get("location", {}).get("id")
            
            if not location_id:
                return JsonResponse({"error": "Location ID not found in webhook data"}, status=400)
            
            # Get authentication token
            try:
                token = GHLAuthCredentials.objects.get(location_id=location_id)
                access_token = token.access_token
            except GHLAuthCredentials.DoesNotExist:
                return JsonResponse({"error": "Authentication credentials not found"}, status=400)
            
            # Check if product name exists in custom data
            custom_data = webhook_data.get("customData", {})
            product_name = custom_data.get("Product Name")
            
            if not product_name:
                return JsonResponse({"error": "Product Name not found in custom data"}, status=400)
            
            # Get or create product
            product_id = get_or_create_product(access_token, location_id, product_name, custom_data)
            
            if not product_id:
                return JsonResponse({"error": "Failed to get or create product"}, status=500)
            
            # Create invoice
            invoice_result = create_invoice(access_token, webhook_data, product_id, product_name)

            print("invoice result: :", invoice_result)
            
            if invoice_result:
                return JsonResponse({"success": True, "invoice_id": invoice_result.get("id")})
            else:
                return JsonResponse({"error": "Failed to create invoice"}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    

class PurchasedServiceDelete(APIView):
    def delete(self, request, id):
        try:
            service=PurchasedService.objects.get(id=id)
            purchase_id = service.purchase.id
            service.delete()
            try:
                purchase = Purchase.objects.get(id=purchase_id)
                serializer = PurchaseDetailSerializer(purchase)
                return Response(serializer.data, status=200)
            except Purchase.DoesNotExist:
                return Response({'error':'not found'}, status=404)
        except PurchasedService.DoesNotExist:
            return Response({'error': 'Purchased service not found'}, status=status.HTTP_404_NOT_FOUND)