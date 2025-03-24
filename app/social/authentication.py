# authentication.py
import base64

from django.contrib.auth import authenticate
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import User

from app.settings import CURRENT_NODE_URL
from .models import Node

class NodeBasicAuthentication(BaseAuthentication):
    """
    Custom authentication for node-to-node communications using HTTP Basic Auth.
    Checks against Node.auth_username and Node.auth_password.
    """
    def authenticate(self, request):
        print("Authentication request:", request, "\n  request data:", request.data)
        auth_header = request.META.get('HTTP_AUTHORIZATION')

        if not auth_header:
            print("  Authentication header is missing")
            return None  # No auth provided; DRF will return a 401

        try:
            auth_type, credentials = auth_header.split(' ', 1)
        except ValueError:
            raise AuthenticationFailed("Invalid authorization header format.")

        if auth_type.lower() != 'basic':
            print('auth_type.lower() is basic')
            return None  # Not basic auth; skip to other authenticators if any

        try:
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
            print(f"{username}, {password}")
        except Exception:
            raise AuthenticationFailed("Invalid basic auth credentials.")

        # Grab node object to attempt to check credentials
        try:
            node = Node.objects.get(auth_username=username)
            print(f'print from authentication.py {node}')
            #node = Node.objects.get(base_url=CURRENT_NODE_URL)
        except Node.DoesNotExist:
            raise AuthenticationFailed("Invalid node credentials.")
        if not node.enabled:
            raise AuthenticationFailed("This node is disabled.")

        # Check login, return user object
        if node.auth_password != password or node.auth_username != username:
            raise AuthenticationFailed("Invalid node credentials.")

        '''
        try:
            user = User.objects.get(username=username)
            user = authenticate(username=username, password=password)
            if user is not None:
                return user, None
        except User.DoesNotExist:
        '''

        # Return the node instance as the authenticated user.
        return (node, None)
