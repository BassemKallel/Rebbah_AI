import secrets
from django.db import models
from django.utils import timezone
from apps.crm.encryption import EncryptedTextField
from .config import BotConfiguration


class Company(models.Model):
    """Client company / shop connected to the platform."""
    name    = models.CharField(max_length=255)
    shop_id = models.CharField(max_length=255, unique=True)

    meta_page_id           = models.CharField(max_length=100, blank=True, null=True, unique=True)
    meta_page_access_token = EncryptedTextField(blank=True, null=True)
    instagram_page_id      = models.CharField(max_length=100, blank=True, null=True, unique=True)
    dashboard_token        = models.CharField(max_length=64, unique=True, blank=True, null=True)

    bot_config = models.OneToOneField(BotConfiguration, on_delete=models.SET_NULL, null=True, blank=True, related_name='company')

    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Companies"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.shop_id})"

    def save(self, *args, **kwargs):
        if not self.dashboard_token:
            self.dashboard_token = secrets.token_hex(32)
        super().save(*args, **kwargs)


class UserProfile(models.Model):
    """Links a Django User to a Company for dashboard authentication."""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin MLOps'),
    ]

    user       = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    company    = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='owner')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        comp_name = self.company.name if self.company else "Global"
        return f"{self.user.username} → {comp_name} ({self.role})"
