from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a new app user'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email for the new user')
        parser.add_argument('password', type=str, help='Password for the new user')
        parser.add_argument('first_name', type=str, help='First name for the new user')
        parser.add_argument('last_name', type=str, help='Last name for the new user')

    def handle(self, *args, **kwargs):
        User = get_user_model()
        email = kwargs['email']
        password = kwargs['password']
        first_name = kwargs['first_name']
        last_name = kwargs['last_name']

        user = User.objects.create_user(email=email, password=password, first_name=first_name, last_name=last_name)
        user.set_aieye_users_role()
        self.stdout.write(self.style.SUCCESS('Successfully created user with Ai Eye User role'))
