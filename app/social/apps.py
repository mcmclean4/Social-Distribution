from django.apps import AppConfig


class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social'

    def ready(self):
        # Import the Node model here, after Django apps are loaded.
        from social.models import Node
        self.ensure_current_node(Node)

    def ensure_current_node(self, Node):
        from django.conf import settings
        current_base_url = getattr(settings, "CURRENT_NODE_URL", None)
        current_name = getattr(settings, "CURRENT_NODE_NAME", "Local Node")
        current_username = getattr(settings, "CURRENT_NODE_USERNAME", None)
        current_password = getattr(settings, "CURRENT_NODE_PASSWORD", None)
        if not current_base_url or not current_username or not current_password:
            # Log an error or handle missing settings.
            return
        Node.objects.get_or_create(
            base_url=current_base_url,
            defaults={
                "name": current_name,
                "auth_username": current_username,
                "auth_password": current_password,
                "enabled": True
            }
        )