from django.db import models
from django.db.models import Count, Q


class PostManager(models.Manager):
    def filtered(self, filter_type='all', authors=None, content_types=None, visibilities=None):
        """
        Returns a QuerySet of posts filtered by:
          - filter_type: 'all' (default), or 'author' (posts by specified authors)
          - authors: a list of author objects. Must use filter_type = 'author' to apply
          - content_types: list of content types (e.g. 'text/plain', 'image/jpeg;base64', etc.)
          - visibilities: list of visibilities (e.g. 'PUBLIC', 'FRIENDS', etc.)

        If visibilities is not provided, only PUBLIC posts are returned
        """
        qs = super().get_queryset().annotate(like_count=Count('likes'))

        # Filter by content types if provided
        if content_types and isinstance(content_types, str) and all(isinstance(item, str) for item in content_types):
            content_types = [content_types]
            qs = qs.filter(contentType__in=content_types)

        # Filter by visibilities if provided; otherwise, exclude DELETED, UNLISTED, and FRIENDS by default
        if visibilities and isinstance(visibilities, list) and all(isinstance(item, str) for item in visibilities):
            # Always exclude DELETED, even if visibilities is provided
            visibilities = [v for v in visibilities if v != 'DELETED']
            qs = qs.filter(visibility__in=visibilities)
            if 'FRIENDS' in visibilities:
                # Only include FRIENDS posts if they are in the author list
                visibilities.remove('FRIENDS')
                qs = qs.filter(
                    Q(visibility__in=visibilities) |
                    (Q(visibility='FRIENDS') & Q(author__in=authors))
                )

        else:
            qs = qs.exclude(visibility__in=['DELETED', 'UNLISTED', 'FRIENDS'])

        # Additional filtering based on user context
        if filter_type == 'author' and authors:
            qs = qs.filter(author__in=authors)

        return qs.order_by('-published')
