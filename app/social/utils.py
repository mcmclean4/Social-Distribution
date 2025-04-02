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


    # Add this function to your inbox processing code
# This adds notifications to your existing follow request processing

def create_follow_request_notification(follow_request, actor_data):
    """
    Creates a notification for a follow request - can be called from your 
    existing follow request handler
    """
    # Skip if the follow request is not pending
    if follow_request.status != 'pending':
        return
    
    # Get actor information
    actor_id = actor_data.get('id', follow_request.follower_id)
    actor_name = actor_data.get('displayName', 'Someone')
    actor_image = actor_data.get('profileImage', BLANK_PIC_URL)
    
    # Create the notification
    try:
        Notification.objects.create(
            recipient=follow_request.followee,
            sender_id=actor_id,
            sender_name=actor_name,
            sender_image=actor_image,
            notification_type='follow_request',
            content_object_id=actor_id,
            content_preview=f"{actor_name} wants to follow you"
        )
        return True
    except Exception as e:
        print(f"Error creating follow request notification: {str(e)}")
        return False

# USAGE EXAMPLE:
# In your existing follow request handling code, add:
"""
# After creating the FollowRequest object
follow_request, created = FollowRequest.objects.get_or_create(
    follower_id=follower_id,
    followee=author,
    defaults={
        'status': 'pending',
        'summary': summary
    }
)

# Add notification for the follow request
if created:
    create_follow_request_notification(follow_request, actor_data)
"""