from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = "Crée un superuser par défaut si aucun n'existe (pour développement)."

    def handle(self, *args, **options):
        if not User.objects.filter(is_superuser=True).exists():
            user = User.objects.create_superuser(
                username='admin',
                email='admin@tiktak.local',
                password='admin'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Superuser créé: username='admin', password='admin'"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING("✓ Un superuser existe déjà.")
            )
