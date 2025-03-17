# authentication.py
import base64
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Node

class NodeBasicAuthentication(BaseAuthentication):
    """
    Custom authentication for node-to-node communications using HTTP Basic Auth.
    Checks against Node.auth_username and Node.auth_password.
    """
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header:
            return None  # No auth provided; DRF will return a 401

        try:
            auth_type, credentials = auth_header.split(' ', 1)
        except ValueError:
            raise AuthenticationFailed("Invalid authorization header format.")

        if auth_type.lower() != 'basic':
            return None  # Not basic auth; skip to other authenticators if any

        try:
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
        except Exception:
            raise AuthenticationFailed("Invalid basic auth credentials.")

        try:
            node = Node.objects.get(auth_username=username)
        except Node.DoesNotExist:
            raise AuthenticationFailed("Invalid node credentials.")

        if not node.enabled:
            raise AuthenticationFailed("This node is disabled.")

        # For production, store hashed passwords and compare securely.
        if node.auth_password != password:
            raise AuthenticationFailed("Invalid node credentials.")

        # Return the node instance as the authenticated user.
        return (node, None)
