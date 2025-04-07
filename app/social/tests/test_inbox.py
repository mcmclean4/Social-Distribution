import base64
import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from django.conf import settings
from social.models import Author, Inbox, FollowRequest, Post, Node
from unittest.mock import patch, MagicMock

"""
test the user stories for sending friend request and being able to see the friend request
Checks the API endpoint Inbox: comment and follow request
"""
class InboxPostTests(TestCase):
    def setUp(self):
        # Set the HOST value expected by your views.
        settings.HOST = "http://localhost:8000/social/"
        
        # Create two users.
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        
        # Create corresponding Author objects.
        # Do not provide explicit IDs so that the custom save() method generates them.
        self.author1 = Author.objects.create(
            user=self.user1,
            id=f"http://localhost:8000/social/api/authors/1",
            displayName="Lara Croft",
            host="http://localhost:8000/social/api/",
            github="http://github.com/laracroft"
        )
        self.author2 = Author.objects.create(
            user=self.user2,
            id=f"http://localhost:8000/social/api/authors/2",
            displayName="Greg Johnson",
            host="http://localhost:8000/social/api/",
            github="http://github.com/gjohnson"
        )
        
        # Refresh objects to get the actual generated IDs.
        self.author1.refresh_from_db()
        self.author2.refresh_from_db()

        # Create an empty Inbox for author1.
        self.inbox = Inbox.objects.create(author=self.author1)

        # Create a remote Node to simulate node-to-node requests.
        self.remote_node = Node.objects.create(
            name="TestNode",
            base_url="http://remotenode.com/",
            auth_username="testnodeuser",
            auth_password="testnodepass",  # Note: In production use hashed passwords.
            enabled=True
        )
        # Set up valid HTTP Basic Auth header using the remote node's credentials.
        credentials = base64.b64encode(b"testnodeuser:testnodepass").decode("utf-8")
        self.remote_auth_header = "Basic " + credentials

        # Initialize the DRF APIClient and set its credentials to simulate a remote node.
        self.client = APIClient()
        self.client.defaults['HTTP_HOST'] = 'localhost:8000'
        self.client.credentials(HTTP_AUTHORIZATION=self.remote_auth_header)

    def test_post_follow_request_to_inbox(self):
        """
        Test posting a follow request to an author's inbox and checks if an inbox object is created in the database.
        This also verifies the The user story, "I want to follow local authors" as it uses the posting to inbox 
        Also checks if the inbox object is created so that author can see the request
        """
        data = {
            "type": "Follow",  
            "summary": f"{self.author2.displayName} wants to follow {self.author1.displayName}",
            "actor": {
                "type": "author",
                "id": self.author2.id,
                "host": self.author2.host,
                "displayName": self.author2.displayName,
                "github": self.author2.github,
                "profileImage": str(self.author2.profileImage) if self.author2.profileImage else "",  # Convert to string or empty
                "page": self.author2.page,
            },
            "object": {
                "type": "author",
                "id": self.author1.id,
                "host": self.author1.host,
                "displayName": self.author1.displayName,
                "github": self.author1.github,
                "profileImage": str(self.author1.profileImage) if self.author1.profileImage else "",  # Convert to string or empty
                "page": self.author1.page,
            }
        }
        # Build the URL using the tail portion of author1's id.
        tail_id = self.author1.id.split('/')[-1]
        url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("received and stored", response.data.get("message", ""))
        
        # Verify in the database that a FollowRequest was created and added to the Inbox.
        inbox = Inbox.objects.get(author=self.author1)
        follow_requests = inbox.inbox_follows.all()
        self.assertEqual(follow_requests.count(), 1)
        follow_request = follow_requests.first()
        self.assertEqual(follow_request.follower_id, self.author2.id)
        self.assertEqual(follow_request.status, "pending")
        self.assertEqual(
            follow_request.summary,
            f"{self.author2.displayName} wants to follow {self.author1.displayName}"
        )

    @patch("social.views.requests.get")
    def test_get_inbox_after_post(self, mock_get):
        """
        Test that after posting a follow request, a GET request returns it correctly.
        This test also checks the database to confirm the follow request exists.
        """
        # First, post the follow request.
        data = {
            "type": "Follow",
            "summary": f"{self.author2.displayName} wants to follow {self.author1.displayName}",
            "actor": {
                "type": "author",
                "id": self.author2.id,
                "host": self.author2.host,
                "displayName": self.author2.displayName,
                "github": self.author2.github,
                "profileImage": str(self.author2.profileImage) if self.author2.profileImage else "",
                "page": self.author2.page,
            },
            "object": {
                "type": "author",
                "id": self.author1.id,
                "host": self.author1.host,
                "displayName": self.author1.displayName,
                "github": self.author1.github,
                "profileImage": str(self.author1.profileImage) if self.author2.profileImage else "",
                "page": self.author1.page,
            }
        }
        tail_id = self.author1.id.split('/')[-1]
        post_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        post_response = self.client.post(post_url, data, format="json")
        self.assertEqual(post_response.status_code, 201)
        
        # Check the database to ensure the FollowRequest is created.
        db_inbox = Inbox.objects.get(author=self.author1)
        self.assertEqual(db_inbox.inbox_follows.count(), 1)
        
        # Patch the requests.get calls used to fetch author details.
        def dummy_get(url, headers):
            dummy = MagicMock()
            if url == self.author1.id:
                dummy.json.return_value = {
                    "id": self.author1.id,
                    "host": self.author1.host,
                    "displayName": self.author1.displayName,
                    "github": self.author1.github,
                    "profileImage": str(self.author1.profileImage) if self.author1.profileImage else "",
                    "page": self.author1.page,
                }
            elif url == self.author2.id:
                dummy.json.return_value = {
                    "id": self.author2.id,
                    "host": self.author2.host,
                    "displayName": self.author2.displayName,
                    "github": self.author2.github,
                    "profileImage": str(self.author2.profileImage) if self.author2.profileImage else "",
                    "page": self.author2.page,
                }
            else:
                dummy.json.return_value = {}
            dummy.raise_for_status.return_value = None
            return dummy

        mock_get.side_effect = dummy_get
        
        # Perform a GET request to retrieve the inbox.
        get_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        
        response_data = get_response.data
        self.assertEqual(response_data.get("type"), "inbox")
        items = response_data.get("items", [])
        # Expect one follow request.
        self.assertEqual(len(items), 1)
        follow_item = items[0]
        self.assertEqual(follow_item.get("type"), "Follow")
        
        # Verify the actor details match author2.
        actor = follow_item.get("actor", {})
        self.assertEqual(actor.get("displayName"), self.author2.displayName)
        # Verify the object details match author1.
        obj = follow_item.get("object", {})
        self.assertEqual(obj.get("displayName"), self.author1.displayName)

    def test_post_comment_to_inbox(self):
        """
        Test posting a comment to an author's inbox and verifying if it is stored correctly.
        """
        # First, create a post
        post = Post.objects.create(
            title="Test Post",
            description="This is a test post description",
            contentType="text/markdown",
            content="This is a test post content.",
            author=self.author1,
            visibility="PUBLIC"
        )
        post.refresh_from_db()

        # Create comment data
        data = {
            "type": "comment",
            "id": f"{self.author2.host}authors/{self.author2.id}/commented/101",
            "post": post.id,
            "comment": "This is a test comment on your post.",
            "contentType": "text/markdown",
            "published": "2025-03-08T23:00:00-07:00",
            "author": {
                "type": "author",
                "id": self.author2.id,
                "host": self.author2.host,
                "displayName": self.author2.displayName,
                "github": self.author2.github,
                "profileImage": str(self.author2.profileImage) if self.author2.profileImage else "",
                "page": self.author2.page,
            }
        }
        
        # Build the inbox URL
        tail_id = self.author1.id.split('/')[-1]
        url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("received and stored", response.data.get("message", ""))
        
        # Verify in the database that the comment was added to the Inbox
        inbox = Inbox.objects.get(author=self.author1)
        comments = inbox.inbox_comments.all()
        self.assertEqual(comments.count(), 1)
        comment = comments.first()
        self.assertEqual(comment.comment, "This is a test comment on your post.")
        self.assertEqual(comment.post, post.id)
        self.assertEqual(comment.author.id, self.author2.id)
