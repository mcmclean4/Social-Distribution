from django.shortcuts import get_object_or_404

from social.models import *


def get_friends(author):
    """
    Return list of author objects that are friends with the given author
    """
    author_id = author.id

    # Find people who mutually follow the given author
    following_ids = set(Follow.objects.filter(follower_id=author_id).values_list("followee_id", flat=True))
    followers_ids = set(Follow.objects.filter(followee_id=author_id).values_list("follower_id", flat=True))
    friends_ids = following_ids.intersection(followers_ids)

    # Get author objects
    friends = []
    for friend in friends_ids:
        friends.append(id_to_author(friend))
    friends.append(author)   # Author is a friend of themselves
    return friends

def id_to_author(id):
    """
    Convert author ID to author object
    """
    return get_object_or_404(Author, id=id)

def get_base_url(url_or_request):
    """
    Extracts the base URL (protocol + domain/IP) from a URL or request object.
    Args:
        url_or_request: Either a URL string or HttpRequest object
    Returns:
        str: Base URL in format "scheme://domain"
    """
    if hasattr(url_or_request, 'build_absolute_uri'):
        # It's a request object
        return f"{url_or_request.scheme}://{url_or_request.get_host()}"
    elif url_or_request:
        # It's a URL string
        parsed_url = urlparse(url_or_request)
        return f"{parsed_url.scheme}://{parsed_url.netloc}"
    return "http://localhost:8000"  # Default fallback
