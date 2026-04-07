"""
create_merchant_user — Management command to create an initial merchant user.

Usage:
    python manage.py create_merchant_user --username admin --password admin123 --shop-id 1LXybpj
    python manage.py create_merchant_user --username admin --password admin123 --shop-id 1LXybpj --email admin@tiktakpro.com
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from apps.crm.models import Company, UserProfile


class Command(BaseCommand):
    help = 'Create a merchant user linked to a Company via UserProfile'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Login username')
        parser.add_argument('--password', required=True, help='Login password')
        parser.add_argument('--shop-id', required=True, help='Company shop_id to link this user to')
        parser.add_argument('--email', default='', help='Email address (optional)')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        shop_id = options['shop_id']
        email = options['email']

        # Validate company exists
        try:
            company = Company.objects.get(shop_id=shop_id)
        except Company.DoesNotExist:
            raise CommandError(f"Company with shop_id='{shop_id}' does not exist.")

        # Create or update User
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_active': True},
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"User '{username}' created."))
        else:
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists — updating password."))
            user.set_password(password)
            if email:
                user.email = email
            user.save()

        # Create or update UserProfile
        profile, p_created = UserProfile.objects.get_or_create(
            user=user,
            defaults={'company': company, 'role': 'owner'},
        )
        if not p_created:
            profile.company = company
            profile.save()
            self.stdout.write(self.style.WARNING(f"Profile updated → {company.name}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Profile created → {company.name} (owner)"))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Merchant user ready:\n"
            f"   Username:  {username}\n"
            f"   Company:   {company.name}\n"
            f"   Shop ID:   {company.shop_id}\n"
            f"   Login at:  POST /api/v1/auth/login/"
        ))
