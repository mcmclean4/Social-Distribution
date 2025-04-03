# notifications_view.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import requests

from .models import Author, Notification

@login_required
def notifications_home(request):
    """
    Main view for the notifications page that shows tabs for likes, comments, etc.
    """
    if not hasattr(request.user, 'author'):
        return redirect('social:register')
        
    author = request.user.author
    
    # Get counts for different notification types
    like_count = Notification.objects.filter(
        recipient=author, 
        notification_type__in=['like_post', 'like_comment'],
        is_read=False
    ).count()
    
    comment_count = Notification.objects.filter(
        recipient=author, 
        notification_type='comment',
        is_read=False
    ).count()
    
    # Get follow request count
    my_author_id = author.id
    inbox_url = f"{my_author_id}/inbox"
    
    try:
        response = requests.get(inbox_url, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        inbox_data = response.json()
        
        # Extract only "follow" requests
        follow_requests = [
            item for item in inbox_data.get("items", [])
            if item.get("type", "").lower() == "follow"
        ]
        follow_count = len(follow_requests)
    except requests.exceptions.RequestException:
        follow_count = 0
    
    context = {
        'my_author_id': author.id,
        'like_count': like_count,
        'comment_count': comment_count,
        'follow_count': follow_count,
        'total_count': like_count + comment_count + follow_count,
        'active_tab': 'home'
    }
    
    # Keep your notifications view name consistent
    return render(request, 'social/notifications_view.html', context)

@login_required
def notifications_likes(request):
    """
    View to display all like notifications
    """
    if not hasattr(request.user, 'author'):
        return redirect('social:register')
        
    author = request.user.author
    
    # Get like notifications
    notifications = Notification.objects.filter(
        recipient=author,
        notification_type__in=['like_post', 'like_comment']
    ).order_by('-created_at')
    
    # Get counts for badges
    comment_count = Notification.objects.filter(
        recipient=author, notification_type='comment', is_read=False
    ).count()
    
    # You can get your follow request count from your existing system
    from .models import FollowRequest
    follow_count = FollowRequest.objects.filter(followee=author, status='pending').count()
    
    # Mark notifications as read
    notifications.filter(is_read=False).update(is_read=True)
    
    context = {
        'my_author_id': author.id,
        'notifications': notifications,
        'like_count': 0,  # Reset since we're viewing them
        'comment_count': comment_count,
        'follow_count': follow_count,
        'active_tab': 'likes'
    }
    
    return render(request, 'social/notifications_likes.html', context)

@login_required
def notifications_comments(request):
    """
    View to display all comment notifications
    """
    if not hasattr(request.user, 'author'):
        return redirect('social:register')
        
    author = request.user.author
    
    # Get comment notifications
    notifications = Notification.objects.filter(
        recipient=author,
        notification_type='comment'
    ).order_by('-created_at')
    
    # Get counts for badges
    like_count = Notification.objects.filter(
        recipient=author, notification_type__in=['like_post', 'like_comment'], is_read=False
    ).count()
    
    # You can get your follow request count from your existing system
    from .models import FollowRequest
    follow_count = FollowRequest.objects.filter(followee=author, status='pending').count()
    
    # Mark notifications as read
    notifications.filter(is_read=False).update(is_read=True)
    
    context = {
        'my_author_id': author.id,
        'notifications': notifications,
        'like_count': like_count,
        'comment_count': 0,  # Reset since we're viewing them
        'follow_count': follow_count,
        'active_tab': 'comments'
    }
    
    return render(request, 'social/notifications_comments.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """
    Mark a specific notification as read
    """
    if not hasattr(request.user, 'author'):
        return redirect('social:register')
        
    author = request.user.author
    notification = get_object_or_404(Notification, id=notification_id, recipient=author)
    
    notification.is_read = True
    notification.save()
    
    # Return to the previous page
    next_url = request.GET.get('next', 'social:notifications_home')
    return redirect(next_url)

@login_required
def mark_all_notifications_read(request):
    """
    Mark all notifications as read
    """
    if not hasattr(request.user, 'author'):
        return redirect('social:register')
        
    author = request.user.author
    Notification.objects.filter(recipient=author, is_read=False).update(is_read=True)
    
    # Return to notifications home
    return redirect('social:notifications_home')

@login_required
def get_notification_count(request):
    """
    endpoint to get unread notification counts for badges
    """
    if request.method == 'GET':
        if not hasattr(request.user, 'author'):
            return JsonResponse({'error': 'User has no author profile'}, status=400)
            
        author = request.user.author
        
        # Count notifications by type
        like_count = Notification.objects.filter(
            recipient=author, 
            notification_type__in=['like_post', 'like_comment'],
            is_read=False
        ).count()
        
        comment_count = Notification.objects.filter(
            recipient=author, 
            notification_type='comment',
            is_read=False
        ).count()
        
        # You can get your follow request count from your existing system
        from .models import FollowRequest
        follow_count = FollowRequest.objects.filter(followee=author, status='pending').count()
        
        # Total count for the main badge
        total_count = like_count + comment_count + follow_count
        
        return JsonResponse({
            'total_count': total_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'follow_count': follow_count
        })
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)