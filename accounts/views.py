from django.shortcuts import render,redirect
from django.conf import settings
from accounts.models import GHLAuthCredentials
import requests
from django.http import JsonResponse
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.utils import fetch_all_contacts


CLIENT_ID = settings.CLIENT_ID
CLIENT_SECRET = settings.CLIENT_SECRET
SCOPES = settings.SCOPES
REDIRECT_URI = settings.REDIRECT_URI
TOKEN_URL = settings.TOKEN_URL
BASE_API_URL = settings.BASE_API_URL



def auth_connect(request):
    auth_url = ("https://marketplace.leadconnectorhq.com/oauth/chooselocation?response_type=code&"
                f"redirect_uri={REDIRECT_URI}&"
                f"client_id={CLIENT_ID}&"
                f"scope={SCOPES}"
                )
    return redirect(auth_url)

def callback(request):
    
    code = request.GET.get('code')

    if not code:
        return JsonResponse({"error": "Authorization code not received from OAuth"}, status=400)

    return redirect(f'{BASE_API_URL}/accounts/auth/tokens?code={code}')



def tokens(request):
    authorization_code = request.GET.get("code")

    if not authorization_code:
        return JsonResponse({"error": "Authorization code not found"}, status=400)

    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": authorization_code,
    }

    response = requests.post(TOKEN_URL, data=data)

    try:
        response_data = response.json()
        if not response_data:
            return

        obj, created = GHLAuthCredentials.objects.update_or_create(
            location_id= response_data.get("locationId"),
            defaults={
                "access_token": response_data.get("access_token"),
                "refresh_token": response_data.get("refresh_token"),
                "expires_in": response_data.get("expires_in"),
                "scope": response_data.get("scope"),
                "user_type": response_data.get("userType"),
                "company_id": response_data.get("companyId"),
                "user_id":response_data.get("userId"),

            }
        )

        fetch_all_contacts(response_data.get("locationId"), response_data.get("access_token"))
        
        
        
        return JsonResponse({
            "message": "Authentication successful",
            "access_token": response_data.get('access_token'),
            "token_stored": True
        })
        
    except requests.exceptions.JSONDecodeError:
        return JsonResponse({
            "error": "Invalid JSON response from API",
            "status_code": response.status_code,
            "response_text": response.text[:500]
        }, status=500)
    




class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        print(email, password)
        
        try:
            user = User.objects.get(email=email)
            print(user.email,'user')
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=400)

        user = authenticate(username=user.username, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user_info':{'email':user.email}
            })
        return Response({'error': 'Invalid credentials'}, status=400)
