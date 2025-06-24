from django.urls import path, include
from data_management_app.views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')

urlpatterns = [
    path("webhook",webhook_handler),
    path('contacts/search/', ContactSearchView.as_view(), name='contact-search'),
    path('api/', include(router.urls)),
    path('purchase/', CreatePurchaseView.as_view(), name='create-purchase'),
    path('user/review/<int:id>/', ReviewView.as_view()),
    path('globalsettings/update/', globalsettingsView.as_view()),
    path('quotes/<int:quoteId>/submit/', FinalSubmition.as_view()),
    path('validate/location/', validate_locationId.as_view()),
    path("create-invoice-webhook",GhlWebhookView.as_view() , name="webhook"),
    path('purchased-service/delete/<int:id>/', PurchasedServiceDelete.as_view()),
]