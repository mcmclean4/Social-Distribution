from django.db import models
from django.contrib.auth.models import User
from social.managers import PostManager
from django.utils import timezone
from urllib.parse import urlparse
import uuid
import os

BLANK_PIC_URL = "https://i.imgur.com/7MUSXf9.png"

def get_base_url(full_url):
    """Extracts the protocol + domain/IP from a full URL."""
    parsed_url = urlparse(full_url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"  # Keeps protocol + domain/IP

# =============================================================================
# Node
# =============================================================================

class Node(models.Model):
    name = models.CharField(max_length=100)
    base_url = models.URLField(unique=True)
    auth_username = models.CharField(max_length=100, unique=True) # TODO: Figure this out
    auth_password = models.CharField(max_length=100) # TODO: Figure this out
    enabled = models.BooleanField(default=True)  # Controls whether this node can communicate
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def is_authenticated(self):
        return True

# =============================================================================
# Author: Represents a user (local or remote) who can post, follow, etc.
# =============================================================================

class Author(models.Model):
    user = models.OneToOneField(to=User, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=50, default='author', editable=False)
    id = models.URLField(primary_key=True, unique=True, editable=False)

    host = models.URLField(null=True, blank=True)
    displayName = models.CharField(max_length=255)
    github = models.CharField(blank=True, null=True,max_length=100)
    github_timestamp = models.DateTimeField(default=timezone.now)
    profileImage = models.URLField(blank=True, default=BLANK_PIC_URL)
    page = models.URLField(blank=True, null=True)
    isAdmin = models.BooleanField(default=False)

    @property
    def friends(self):
        """
        Returns a QuerySet of all authors who are mutual followers.
        """
        followees = Follow.objects.filter(follower_id=self.id).values_list('followee', flat=True)
        followers = Follow.objects.filter(followee=self).values_list('follower_id', flat=True)

        # Mutual followers = people who follow this user & are followed back
        mutual_followers = Author.objects.filter(id__in=followees).filter(id__in=followers)
        return mutual_followers
    
    @property
    def remote_followers(self):
        """
        Returns a list of follower IDs that start with different hosts
        """
        # Get current author's host
        my_host = get_base_url(self.host) if self.host else "http://localhost:8000"
        
        # Get all follower IDs
        follower_ids = Follow.objects.filter(followee=self).values_list('follower_id', flat=True)
        
        # Filter for foreign follower IDs that don't start with current host
        foreign_followers = [
            follower_id for follower_id in follower_ids
            if not follower_id.startswith(my_host)
        ]
        
        return foreign_followers

    def save(self, *args, **kwargs):   
        if self._state.adding and not self.id:
            # Get the base URL for the host
            base_url = get_base_url(self.host) if self.host else "http://localhost:8000"
            
            # Get the largest User ID and add 1
            largest_user_id = User.objects.all().order_by('-id').values_list('id', flat=True).first() or 0
            next_id = largest_user_id + 1
            
            # Make sure this ID doesn't already exist (just in case)
            while Author.objects.filter(id=f"{base_url}/social/api/authors/{next_id}").exists():
                next_id += 1
            
            # Set the new author's ID and page URL
            self.id = f"{base_url}/social/api/authors/{next_id}"
            self.page = f"{base_url}/social/profile/{next_id}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.displayName


# =============================================================================
# Post: Represents a social media post with likes, comments, etc.
# =============================================================================

class Post(models.Model):
    POST_CHOICES = [
        ('post', 'post'),
        ('comment', 'Comment'),
    ]

    CONTENT_TYPE_CHOICES = [
        ('text/plain', 'Plain Text'),
        ('text/markdown', 'Markdown'),
        ('application/base64', 'Base64 Image'),
        ('image/png;base64', 'PNG'),
        ('image/jpeg;base64', 'JPEG'),
        ('video/mp4;base64', 'MP4 Video'),
        ('video/webm;base64', 'WebM Video'),
    ]

    CONTENT_VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('FRIENDS', 'Friends'),
        ('UNLISTED', 'Unlisted'),
        ('DELETED', 'Deleted'),
    ]

    objects = PostManager()
    type = models.CharField(max_length=50, choices=POST_CHOICES, default='post')
    title = models.CharField(max_length=255)
    id = models.URLField(unique=True, editable=False)
    page = models.URLField(blank=True, null=True)
    description = models.CharField(max_length=255)
    contentType = models.CharField(max_length=50, choices=CONTENT_TYPE_CHOICES)
    content = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    published = models.DateTimeField(auto_now_add=True)
    visibility = models.CharField(max_length=50, choices=CONTENT_VISIBILITY_CHOICES)
    
    internal_id = models.AutoField(primary_key=True, editable=False)

    @property
    def comments(self):
        from .models import Comment
        return Comment.objects.filter(post=self.id)
    
    @property
    def likes(self):
        """
        Returns all Like objects associated with this post.
        """
        return Like.objects.filter(object=self.id)
    
    @property
    def likes_count(self):
        """
        Returns the number of likes for this post.
        """
        return self.likes.count()
    

    class Meta:
        ordering = ['-published']

    def __str__(self):
        return self.title


    def save(self, *args, **kwargs):
        is_new = self._state.adding

        # Only auto-generate ID if it's not provided (i.e., local post)
        if is_new and not self.id:
            super().save(*args, **kwargs)  # Save first so internal_id is assigned

            author_id = self.author.id.split('/')[-1]
            base_url = get_base_url(self.author.host) if self.author.host else "http://localhost:8000"

            self.id = f"{base_url}/social/api/authors/{author_id}/posts/{self.internal_id}"
            self.page = f"{base_url}/social/post/{self.internal_id}/"

            super().save(update_fields=["id", "page"])
        else:
            super().save(*args, **kwargs)




# =============================================================================
# Comment: Represents a comment on a post.
# =============================================================================



class Comment(models.Model):
    type = models.CharField(max_length=10, default="comment")
    id = models.URLField(primary_key=True)
    internal_id = models.UUIDField(default=uuid.uuid4, editable=False)  # Remove unique=True for now
    author = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()  
    contentType = models.CharField(max_length=50, default="text/markdown")
    published = models.DateTimeField(default=timezone.now)
    post = models.URLField() 
    
    def save(self, *args, **kwargs):
        # Generate the ID if it's not set
        if not self.id:
            # Format: http://[host]/api/authors/[author_id]/commented/[internal_id]

            # Extract author ID from the author object
            author_id_part = self.author.id.split('/')[-1]
            
            base_url = get_base_url(self.author.id)

            # Extract author ID from the author object
            author_id_part = self.author.id.split('/')[-1]

            # Construct the unique comment ID
            self.id = f"{base_url}/social/api/authors/{author_id_part}/commented/{self.internal_id}"     
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-published']
    
    def __str__(self):
        return f"Comment by {self.author.displayName} on {self.published.strftime('%Y-%m-%d')}"

    def get_likes_count(self):
        from .models import Like
        return Like.objects.filter(object=self.id).count()
# =============================================================================
# Follow: Represents a relationship between two authors (follower and followee).
# =============================================================================

class FollowRequest(models.Model):
    """
    Represents a follow request stored in the inbox of the followee.
    """
    summary = models.CharField(max_length=255, blank=True)
    follower_id = models.CharField(max_length=255)  # Store remote/local follower as FQID       #Follower does not have to be author in our node
    followee = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='follow_requests')

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower_id", "followee")  # Prevent duplicate follow requests

    def __str__(self):
        return f"{self.follower_id} -> {self.followee.displayName} ({self.status})"



class Follow(models.Model):
    """
    Represents an actual follow relationship after approval.
    """
    follower_id = models.CharField(max_length=255)  # Store remote/local follower as FQID
    followee = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='followers')

    class Meta:
        unique_together = ("follower_id", "followee")  # Prevent duplicate follow entries

    def __str__(self):
        return f"{self.follower_id} follows {self.followee.displayName}"

class Comments(models.Model):
    type = models.CharField(max_length=50)

class Like(models.Model):
    type = models.CharField(max_length=10, default="like")
    id = models.URLField(primary_key=True)
    author = models.ForeignKey('Author', on_delete=models.CASCADE, related_name='liked_items')
    object = models.URLField()  # URL of the liked object (post or comment)
    published = models.DateTimeField(default=timezone.now)
    
    def save(self, *args, **kwargs):
        if not self.id:  # Only generate an ID if none is provided
            # Extract base URL from the author's ID dynamically
            base_url = get_base_url(self.author.id)

            # Extract author ID from the author object
            author_id_part = self.author.id.split('/')[-1]

            # Generate a unique ID for this like
            like_id = uuid.uuid4()

            # Construct the unique like ID
            self.id = f"{base_url}/social/api/authors/{author_id_part}/liked/{like_id}"

        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-published']
        unique_together = ('author', 'object')  # Prevent duplicate likes

class Likes(models.Model):
    type = models.CharField(max_length=50)


class Posts(models.Model):
    type = models.CharField(max_length=50)
    pageNumber = models.IntegerField()
    size = models.IntegerField()
    count = models.IntegerField()
    src = models.ForeignKey(Post, on_delete=models.CASCADE)

class Inbox(models.Model):
    author = models.ForeignKey('Author', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, default='inbox')
    inbox_posts = models.ManyToManyField(Post,blank = True)
    inbox_likes = models.ManyToManyField(Like, blank=True)
    inbox_follows = models.ManyToManyField(FollowRequest, blank=True)
    inbox_comments = models.ManyToManyField(Comment,  blank=True)

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('like_post', 'Like on Post'),
        ('like_comment', 'Like on Comment'),
        ('comment', 'New Comment'),
        ('follow_request', 'Follow Request'),
    ]
    
    recipient = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='notifications')
    sender_id = models.CharField(max_length=255)  # Store sender ID as URL string
    sender_name = models.CharField(max_length=255)  # Store display name for quick access
    sender_image = models.URLField(default=BLANK_PIC_URL)
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    content_object_id = models.URLField()  # URL to the post/comment/like object
    content_object_page = models.URLField()
    
    content_preview = models.CharField(max_length=100, blank=True)  # Short preview of content
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.sender_name} {self.get_notification_type_display()} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"