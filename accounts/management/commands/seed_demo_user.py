"""
Management command to seed the demo user for testing/deployment.
Usage: python manage.py seed_demo_user
"""

from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'Creates a demo user for testing (demo@vai.com / demo1234)'

    def handle(self, *args, **options):
        email = 'demo@vai.com'
        password = 'demo1234'

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'Demo user "{email}" already exists.'))
            return

        User.objects.create_user(
            email=email,
            password=password,
            full_name='Demo User',
        )
        self.stdout.write(self.style.SUCCESS(f'Demo user created: {email} / {password}'))
