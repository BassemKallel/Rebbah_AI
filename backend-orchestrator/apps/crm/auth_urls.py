"""
auth_urls.py — URL routing for JWT authentication endpoints.

Mounted at: /api/v1/auth/
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .auth_views import LoginView, MeView, ChangePasswordView

urlpatterns = [
    path('login/',           LoginView.as_view(),          name='auth-login'),
    path('refresh/',         TokenRefreshView.as_view(),   name='auth-refresh'),
    path('me/',              MeView.as_view(),              name='auth-me'),
    path('change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
]
