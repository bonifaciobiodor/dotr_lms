import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

logger = logging.getLogger(__name__)


class ExternalAPIBackend(ModelBackend):
    """
    Authenticates against the external DOTR HRIS API.
    On success, creates or updates the local user with employee data.
    Falls back to local database auth if the API is unreachable.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()

        # Try external API authentication
        user = self._authenticate_via_api(username, password, User)
        if user is not None:
            return user

        # Fallback: try local database authentication
        return super().authenticate(request, username=username, password=password, **kwargs)

    def _authenticate_via_api(self, username, password, User):
        try:
            # Step 1: Login to external HRIS API
            login_response = requests.post(
                f'{settings.HRIS_URL}/login',
                json={'username': username, 'password': password},
                headers={'Authorization': f'Bearer {settings.HRIS_TOKEN}'},
                timeout=10,
            )
            login_data = login_response.json()

            if login_data.get('status') != 'success':
                return None

            access_token = login_data['data']['authentication']['access_token']

            # Step 2: Fetch user details using the login access token
            user_response = requests.get(
                f'{settings.HRIS_URL}/user',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10,
            )
            api_user = user_response.json()
            employee = api_user['data']['employee']

            # Step 3: Create or update local user
            employee_id = str(employee['id'])

            # Look up by employee_id first, then by username
            try:
                user = User.objects.get(employee_id=employee_id)
            except User.DoesNotExist:
                user, _ = User.objects.get_or_create(
                    username=username.lower(),
                    defaults={
                        'first_name': employee['first_name'].title(),
                        'last_name': employee['last_name'].title(),
                        'employee_id': employee_id,
                    }
                )

            # Update user fields from HRIS
            user.set_password(password)
            user.username = username.lower()
            user.first_name = employee['first_name'].title()
            user.last_name = employee['last_name'].title()
            user.email = employee.get('email', '').lower()
            user.employee_id = employee_id
            if employee.get('employee_number'):
                user.employee_id = employee['employee_number']
            user.save()

            return user

        except requests.RequestException:
            logger.warning('External HRIS API unreachable, falling back to local auth.')
            return None
        except (KeyError, ValueError):
            logger.warning('Unexpected HRIS API response format.')
            return None
