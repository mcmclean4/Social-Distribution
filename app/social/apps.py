from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver


class SocialConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social'

    def ready(self):
        # Register the signal handler
        post_migrate.connect(self.initialize_node, sender=self)
        import social.signals

    def initialize_node(self, sender, **kwargs):
        # Import here to avoid app registry not ready errors
        from social.models import Node
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