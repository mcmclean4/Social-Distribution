import traceback
import requests
from django.conf import settings
from .models import Author, Post, FollowRequest, Inbox, Like, Comment, Node, Follow

def distribute_likes(like_obj, data, content_author_id):
    try:
        print(f"Distributing like to followers of {content_author_id}")
        try:
            content_author = Author.objects.get(id=content_author_id)
        except Author.DoesNotExist:
            print(f"Content author not found for ID: {content_author_id}")
            return
            
        liker = data['author']
        liker_id = liker['id']
        
        # Get local and remote followers using the content author's properties
        local_follower_ids = Follow.objects.filter(followee=content_author).values_list('follower_id', flat=True)
        remote_follower_ids = content_author.remote_followers
        
        print(f"Found {len(local_follower_ids)} local followers and {len(remote_follower_ids)} remote followers")
        
        
        # Process remote followers
        for follower_id in remote_follower_ids:
            try:
                # Skip if this is the original liker
                if liker_id == follower_id:
                    print(f"Skipping original liker: {follower_id}")
                    continue
                
                print(f"Processing remote follower: {follower_id}")
                
                # Get the domain part of the follower ID
                follower_host = None
                if '//' in follower_id:
                    follower_host = follower_id.split('//')[1].split('/')[0]
                
                # Find the node for this follower
                node = None
                if follower_host:
                    node = Node.objects.filter(base_url__contains=follower_host).first()
                
                if not node:
                    print(f"No node found for remote follower: {follower_id}")
                    continue
                
                # Construct the inbox URL
                inbox_url = f"{follower_id}/inbox"
                if inbox_url.endswith('//inbox'):
                    inbox_url = inbox_url.replace('//inbox', '/inbox')
                
                print(f"Sending like to remote follower: {follower_id} at {inbox_url}")
                
                # Send HTTP request to the follower's inbox
                response = requests.post(
                    inbox_url,
                    json=data,
                    auth=(node.auth_username, node.auth_password),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code >= 400:
                    print(f"Error sending like to {follower_id}'s inbox: {response.status_code}")
                else:
                    print(f"Successfully sent like to {follower_id}'s inbox")
        
            except Exception as e:
                print(f"Error processing remote follower {follower_id}: {str(e)}")
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Exception in distribute_likes: {str(e)}")
        traceback.print_exc()

def distribute_comments(comment_obj, data, content_author_id):
    try:
        print(f"Distributing comment to followers of {content_author_id}")
        try:
            content_author = Author.objects.get(id=content_author_id)
        except Author.DoesNotExist:
            print(f"Content author not found for ID: {content_author_id}")
            return
            
        commenter = data['author']
        commenter_id = commenter['id']
        
        # Get local and remote followers using the content author's properties
        local_follower_ids = Follow.objects.filter(followee=content_author).values_list('follower_id', flat=True)
        remote_follower_ids = content_author.remote_followers
        
        print(f"Found {len(local_follower_ids)} local followers and {len(remote_follower_ids)} remote followers")
        
        
        # Process remote followers
        for follower_id in remote_follower_ids:
            try:
                # Skip if this is the original commenter
                if commenter_id == follower_id:
                    print(f"Skipping original commenter: {follower_id}")
                    continue
                
                print(f"Processing remote follower: {follower_id}")
                
                # Get the domain part of the follower ID
                follower_host = None
                if '//' in follower_id:
                    follower_host = follower_id.split('//')[1].split('/')[0]
                
                # Find the node for this follower
                node = None
                if follower_host:
                    node = Node.objects.filter(base_url__contains=follower_host).first()
                
                if not node:
                    print(f"No node found for remote follower: {follower_id}")
                    continue
                
                # Construct the inbox URL
                inbox_url = f"{follower_id}/inbox"
                if inbox_url.endswith('//inbox'):
                    inbox_url = inbox_url.replace('//inbox', '/inbox')
                
                print(f"Sending comment to remote follower: {follower_id} at {inbox_url}")
                
                # Send HTTP request to the follower's inbox
                response = requests.post(
                    inbox_url,
                    json=data,
                    auth=(node.auth_username, node.auth_password),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code >= 400:
                    print(f"Error sending comment to {follower_id}'s inbox: {response.status_code}")
                else:
                    print(f"Successfully sent comment to {follower_id}'s inbox")
        
            except Exception as e:
                print(f"Error processing remote follower {follower_id}: {str(e)}")
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Exception in distribute_comments: {str(e)}")
        traceback.print_exc()


def distribute_comment_likes(like_obj, data, content_author_id):
    """
    Distribute a comment like to followers of the post author.
    Similar to distribute_likes but specifically for comment likes.
    
    Args:
        like_obj: The Like object
        data: The formatted like data to send
        content_author_id: ID of the post author whose followers should receive the like
    """
    try:
        print(f"Distributing comment like to followers of {content_author_id}")
        try:
            content_author = Author.objects.get(id=content_author_id)
        except Author.DoesNotExist:
            print(f"Content author not found for ID: {content_author_id}")
            return
            
        liker = data['author']
        liker_id = liker['id']
        
        # Get local and remote followers using the content author's properties
        local_follower_ids = Follow.objects.filter(followee=content_author).values_list('follower_id', flat=True)
        remote_follower_ids = content_author.remote_followers
        
        print(f"Found {len(local_follower_ids)} local followers and {len(remote_follower_ids)} remote followers")
        
        # Process remote followers
        for follower_id in remote_follower_ids:
            try:
                # Skip if this is the original liker
                if liker_id == follower_id:
                    print(f"Skipping original liker: {follower_id}")
                    continue
                
                print(f"Processing remote follower: {follower_id}")
                
                # Get the domain part of the follower ID
                follower_host = None
                if '//' in follower_id:
                    follower_host = follower_id.split('//')[1].split('/')[0]
                
                # Find the node for this follower
                node = None
                if follower_host:
                    node = Node.objects.filter(base_url__contains=follower_host).first()
                
                if not node:
                    print(f"No node found for remote follower: {follower_id}")
                    continue
                
                # Construct the inbox URL
                inbox_url = f"{follower_id}/inbox"
                if inbox_url.endswith('//inbox'):
                    inbox_url = inbox_url.replace('//inbox', '/inbox')
                
                print(f"Sending comment like to remote follower: {follower_id} at {inbox_url}")
                
                # Send HTTP request to the follower's inbox
                response = requests.post(
                    inbox_url,
                    json=data,
                    auth=(node.auth_username, node.auth_password),
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                
                if response.status_code >= 400:
                    print(f"Error sending comment like to {follower_id}'s inbox: {response.status_code}")
                else:
                    print(f"Successfully sent comment like to {follower_id}'s inbox")
        
            except Exception as e:
                print(f"Error processing remote follower {follower_id}: {str(e)}")
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Exception in distribute_comment_likes: {str(e)}")
        traceback.print_exc()