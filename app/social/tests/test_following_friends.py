import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from django.conf import settings
from social.models import Author, Inbox, FollowRequest, Follow
from unittest.mock import patch, MagicMock

"""
This tests the user stories for approving and denying the follow-request
And unfollow someone
Checks the API endpoints for followers and an individual follower
"""


class FollowersAPITests(TestCase):
    def setUp(self):
        # Set the HOST value expected by your views.
        settings.HOST = "http://localhost:8000/social/"
        
        # Create two users.
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        
        # Create corresponding Author objects without specifying an explicit ID.
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
        # Refresh to obtain the actual generated IDs.
        self.author1.refresh_from_db()
        self.author2.refresh_from_db()
        
        #assign each user the corresponding author object.
        self.user1.author = self.author1
        self.user1.save()
        self.user2.author = self.author2
        self.user2.save()
        
        # Create an empty Inbox for author1.
        self.inbox = Inbox.objects.create(author=self.author1)
        
        # Initialize the DRF APIClient.
        self.client = APIClient()
        self.client.defaults['HTTP_HOST'] = 'localhost:8000'
        

    def post_follow_request(self):
        """
        Helper method to simulate posting a follow request from author2 to author1.
        """
        data = {
            "type": "Follow",  # Must match view logic (capital F)
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
                "profileImage": str(self.author1.profileImage) if self.author1.profileImage else "",
                "page": self.author1.page,
            }
        }
        # The inbox endpoint expects the "author_id" parameter to be the tail of author1's id.
        tail_id = self.author1.id.split('/')[-1]
        url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        return self.client.post(url, data, format="json")

    def test_accept_follow_request(self):
        """
        Test accepting a follow request:
          1. Post a follow request to author1's inbox.
          2. Approve the follow request via a PUT to the followers API.
          3. Verify the FollowRequest status is updated and a Follow is created.
          4. Verify that GET endpoints for followers return the correct data.
        """
        # Post the follow request.
        post_response = self.post_follow_request()
        self.assertEqual(post_response.status_code, 201)
        
        tail_id = self.author1.id.split('/')[-1]

        # Approve the follow request by sending a PUT request to the followers API.
        self.client.force_login(self.user1)  # Log in user1 (the followee)
        followers_url = reverse("social:get_followers", kwargs={"author_id": tail_id})
        put_data = {"id": self.author2.id}
        put_response = self.client.put(followers_url, data=put_data, format="json")

        self.assertEqual(put_response.status_code, 200)  # Expecting 200

        self.assertIn("approved", put_response.data.get("message", "").lower())
        
        # Check in the database that the FollowRequest status is now "accepted".
        follow_request = FollowRequest.objects.filter(followee=self.author1, follower_id=self.author2.id).first()
        self.assertIsNotNone(follow_request)
        self.assertEqual(follow_request.status, "accepted")
        
        # Verify that a Follow relationship has been created.
        follow = Follow.objects.filter(followee=self.author1, follower_id=self.author2.id).first()
        self.assertIsNotNone(follow)
        
        # Now check the GET method for followers.
        get_url = reverse("social:get_followers", kwargs={"author_id": tail_id})
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        followers_list = get_response.data.get("items", [])
        self.assertEqual(len(followers_list), 1)
        self.assertEqual(followers_list[0].get("displayName"), self.author2.displayName)
        
        # Also check the individual follower endpoint.
        individual_url = reverse("social:manage_follower", kwargs={"author_id": tail_id, "follower_fqid": self.author2.id})
        individual_response = self.client.get(individual_url)
        self.assertEqual(individual_response.status_code, 200)
        self.assertEqual(individual_response.data.get("displayName"), self.author2.displayName)

    def test_deny_follow_request(self):
        """
        Test denying a follow request:
          1. Post a follow request to author1's inbox.
          2. Deny the follow request by sending a DELETE request to the inbox endpoint.
          3. Verify the FollowRequest status is updated to "denied".
        """
        post_response = self.post_follow_request()
        self.assertEqual(post_response.status_code, 201)
        
        tail_id = self.author1.id.split('/')[-1]
        inbox_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        
        delete_data = {"follower_id": self.author2.id}
        delete_response = self.client.delete(inbox_url, data=json.dumps(delete_data), content_type="application/json")
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn("denied", delete_response.data.get("message", "").lower())
        
        follow_request = FollowRequest.objects.filter(followee=self.author1, follower_id=self.author2.id).first()
        self.assertIsNotNone(follow_request)
        self.assertEqual(follow_request.status, "denied")

    def test_unfollow(self):
        """
        Test unfollowing:
        1. Create a Follow relationship (simulate that author2 is following author1).
        2. Authenticate as user2 (the follower) and send a DELETE request to `/social/unfollow/`.
        3. Verify the response is 200 and that the Follow object is removed.
        """
        # Create a Follow relationship.
        Follow.objects.create(followee=self.author1, follower_id=self.author2.id)
        self.assertEqual(Follow.objects.filter(followee=self.author1, follower_id=self.author2.id).count(), 1)

        # Use force_login()
        self.client.force_login(self.user2)


        unfollow_url = reverse("social:unfollow")

        delete_data = json.dumps({"followee_id": self.author1.id})
        response = self.client.delete(unfollow_url, data=delete_data, content_type="application/json")

        try:
            response_data = response.json()
            print("Unfollow Response Data:", response_data)  # Debugging Output
        except json.JSONDecodeError:
            print("Error: Response is not valid JSON")
            response_data = {}

        # Ensure response is 200 (success)
        self.assertEqual(response.status_code, 200)
        self.assertIn("unfollowed successfully", response_data.get("message", "").lower())

        # Ensure the Follow relationship is removed
        self.assertEqual(Follow.objects.filter(followee=self.author1, follower_id=self.author2.id).count(), 0)
