from django.urls import path
from data_management_app.views import *

urlpatterns = [
    path("webhook",webhook_handler),
    path('contacts/search/', ContactSearchView.as_view(), name='contact-search'),
]