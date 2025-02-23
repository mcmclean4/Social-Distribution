from django.db import models
from django.db.models import Count


class PostManager(models.Manager):
    def filtered(self, filter_type='all', author=None, content_types=None, visibilities=None):
        """
        Returns a QuerySet of posts filtered by:
          - content_types: a string or list of content types (e.g. 'text/plain', 'image/jpeg;base64', etc.)
          - visibilities: a string or list of visibilities (e.g. 'PUBLIC', 'FRIENDS', etc.)
          - filter_type: 'all' (default), or 'user' (posts by a specific user)

        If visibilities is not provided, DELETED and UNLISTED posts are excluded by default.
        """
        qs = super().get_queryset().annotate(like_count=Count('likes'))

        # Filter by content types if provided
        if content_types:
            if isinstance(content_types, str):
                content_types = [content_types]
            qs = qs.filter(contentType__in=content_types)

        # Filter by visibilities if provided; otherwise, exclude DELETED and UNLISTED by default
        if visibilities:
            print("Pre visibility query:", qs)
            if isinstance(visibilities, str):
                if visibilities == 'ALL':
                    visibilities = ['PUBLIC', 'FRIENDS', 'UNLISTED', 'DELETED']
                else:
                    visibilities = [visibilities]
            qs = qs.filter(visibility__in=visibilities)
            print("Post visibility query:", qs)
        else:
            qs = qs.exclude(visibility__in=['DELETED', 'UNLISTED'])

        # Additional filtering based on user context
        if filter_type == 'author' and author:
            qs = qs.filter(author=author)

        return qs.order_by('-published')
