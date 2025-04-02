# signals.py - Create this file in your app directory
from django.db.models.signals import post_save
from django.dispatch import receiver
from urllib.parse import urlparse

from .models import Like, Comment, FollowRequest, Post, Notification, Author

def get_author_from_url(url):
    """
    Helper function to get Author instance from a URL string
    """
    from django.core.exceptions import ObjectDoesNotExist
    
    try:
        # For posts, extract the author ID from the URL
        # Example: http://localhost:8000/social/api/authors/1/posts/5
        parts = url.split('/')
        if 'authors' in parts and 'posts' in parts:
            # Find the author index and extract the ID
            author_idx = parts.index('authors')
            if author_idx + 1 < len(parts):
                author_id = parts[author_idx + 1]
                
                # Reconstruct the base author URL
                base_url = urlparse(url)
                author_url = f"{base_url.scheme}://{base_url.netloc}/social/api/authors/{author_id}"
                
                try:
                    return Author.objects.get(id__startswith=author_url)
                except ObjectDoesNotExist:
                    return None
    except (IndexError, ValueError):
        return None
    
    return None

@receiver(post_save, sender=Like)
def create_like_notification(sender, instance, created, **kwargs):
    """
    Create notification when a like is created
    """
    if not created:
        return
    
    # Determine if this is a like on a post or comment
    target_url = instance.object
    notification_type = 'like_post'  # Default to post
    content_page_url = None
    
    # Try to find the post first
    try:
        post = Post.objects.get(id=target_url)
        recipient = post.author
        content_preview = post.title[:100]
        content_page_url = post.page
    except Post.DoesNotExist:
        # Check if it's a comment like
        try:
            comment = Comment.objects.get(id=target_url)
            recipient = comment.author
            content_preview = comment.comment[:100]
            notification_type = 'like_comment'
            comment_post = Post.objects.get(id = comment.post)
            content_page_url = comment_post.page
        except Comment.DoesNotExist:
            # Can't find the liked object, skip
            return
    
    # Don't create notification if the author is liking their own content
    if instance.author.id == recipient.id:
        return
    
    # Don't create notification if the recipient is not a local user
    if not recipient.user:
        return
    
    # Create the notification
    Notification.objects.create(
        recipient=recipient,
        sender_id=instance.author.id,
        sender_name=instance.author.displayName,
        sender_image=instance.author.profileImage,
        notification_type=notification_type,
        content_object_id=target_url,
        content_object_page=content_page_url,
        content_preview=content_preview
    )

@receiver(post_save, sender=Comment)
def create_comment_notification(sender, instance, created, **kwargs):
    """
    Create notification when a comment is created
    """
    if not created:
        return
    
    # Find the post this comment is on
    try:
        post = Post.objects.get(id=instance.post)
        post_url = instance.post
        post_author = get_author_from_url(post_url)
        
        if not post_author:
            return
            
        # Don't create notification for self-comments
        if instance.author.id == post_author.id:
            return
            
        # Don't create notification if the recipient is not a local user
        if not post_author.user:
            return
            
        Notification.objects.create(
            recipient=post_author,
            sender_id=instance.author.id,
            sender_name=instance.author.displayName,
            sender_image=instance.author.profileImage,
            notification_type='comment',
            content_object_id=post_url,
            content_object_page=post.page,
            content_preview=instance.comment[:100]
        )
    except Exception as e:
        print(f"Error creating comment notification: {str(e)}")
        # If anything fails, skip creating the notification
        return

@receiver(post_save, sender=FollowRequest)
def create_follow_request_notification(sender, instance, created, **kwargs):
    """
    Create notification for new follow requests
    """
    if not created or instance.status != 'pending':
        return
    
    # Don't create notification if the recipient is not a local user
    if not instance.followee.user:
        return
    
    # Try to get the follower author
    try:
        follower = Author.objects.get(id=instance.follower_id)
        sender_name = follower.displayName
        sender_image = follower.profileImage
    except Author.DoesNotExist:
        # If follower is remote, use default values
        sender_name = "Someone"
        sender_image = BLANK_PIC_URL
    
    Notification.objects.create(
        recipient=instance.followee,
        sender_id=instance.follower_id,
        sender_name=sender_name,
        sender_image=sender_image,
        notification_type='follow_request',
        content_object_id=instance.follower_id,
        content_preview=f"{sender_name} wants to follow you"
    )