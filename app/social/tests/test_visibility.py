from .test_setup import TestSetUp
from social.models import Post, Author, Follow
from django.contrib.auth.models import User
from django.urls import reverse

class VisibilityAPITests(TestSetUp):
    def setUp(self):
        # Call parent setup
        super().setUp()
        
        # Create test users
        self.user1 = User.objects.create_user(username="user1", password="password")
        self.user2 = User.objects.create_user(username="user2", password="password")
        self.user3 = User.objects.create_user(username="user3", password="password")

        # Create test authors
        self.author1 = Author.objects.create(
            user=self.user1, 
            id=f"http://localhost:8000/social/api/authors/1", 
            displayName="Visibility Tester", 
            host="http://localhost:8000/social/api/")
        
        self.author2 = Author.objects.create(
            user=self.user2, 
            id=f"http://localhost:8000/social/api/authors/2", 
            displayName="Friend User", 
            host="http://localhost:8000/social/api/")
        
        self.author3 = Author.objects.create(
            user=self.user3, 
            id=f"http://localhost:8000/social/api/authors/3", 
            displayName="Non-Friend User", 
            host="http://localhost:8000/social/api/")
        
        # Setup friendships
        # Author1 and Author2 are mutual followers (friends)
        Follow.objects.create(follower_id=self.author1.id, followee=self.author2)
        Follow.objects.create(follower_id=self.author2.id, followee=self.author1)
        
        # Create different visibility posts
        self.public_post = Post.objects.create(
            author=self.author1,
            title="Public Post",
            content="This is a public post",
            contentType="text/plain",
            visibility="PUBLIC",
            description="Public test post"
        )
        
        self.friends_post = Post.objects.create(
            author=self.author1,
            title="Friends Only Post",
            content="This is a friends-only post",
            contentType="text/plain",
            visibility="FRIENDS",
            description="Friends test post"
        )
        
        self.unlisted_post = Post.objects.create(
            author=self.author1,
            title="Unlisted Post",
            content="This is an unlisted post",
            contentType="text/plain",
            visibility="UNLISTED",
            description="Unlisted test post"
        )
    
    def test_public_post_visibility(self):
        """Test that PUBLIC posts are visible to everyone"""
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Public Post")
        
        # Should be visible to friends
        friend_visible_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(friend_visible_posts.count(), 1)
        
        # Should be visible to non-friends
        non_friend_visible_posts = Post.objects.filter(author=self.author1, visibility="PUBLIC")
        self.assertEqual(non_friend_visible_posts.count(), 1)
        
        author_id = self.author1.id.split('/')[-1]
        
        # Call the API to get posts for author1
        url = reverse("social:api_get_author_and_all_post", kwargs={"id": author_id})
        response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        # Test both model and API
        # First verify the model count
        public_posts_model = Post.objects.filter(author=self.author1, visibility="PUBLIC").count()
        
        # Now test both with assertions
        # For model verification:
        self.assertEqual(public_posts_model, 1)
        
        # For API verification - should get 200 OK response
        self.assertEqual(response.status_code, 200)
        
        # Check that API response contains the public post
        found_public_post = False
        for post in response.data.get("posts", []):
            if post.get("title") == "Public Post":
                found_public_post = True
                self.assertEqual(post.get("visibility"), "PUBLIC")
        
        self.assertTrue(found_public_post, "Public post should be returned by the API")
        print(f"API public post visibility test passed")
    
    def test_friends_post_visibility(self):
        """Test that FRIENDS posts are only visible to friends"""
        # Test in db first
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="FRIENDS")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Friends Only Post")
        
        # Verify author2 is friends with author1
        self.assertIn(self.author2, self.author1.friends)
        
        # Use the PostManager's get_posts_for_author
        friend_visible_posts = Post.objects.filter(
            author=self.author1, 
            visibility="FRIENDS"
        )
        self.assertEqual(friend_visible_posts.count(), 1)
        
        ######################################################


        # Get author IDs for API calls
        author1_id = self.author1.id.split('/')[-1]
        
        # Test visibility for a friend (user2/author2)
        self.client.logout()
        self.client.force_login(self.user2)
        
        # Call the API to get posts for author1 from perspective of user2 (a friend)
        url = reverse("social:api_get_author_and_all_post", kwargs={"id": author1_id})
        friend_response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        # Check response status
        self.assertEqual(friend_response.status_code, 200)
        
        # Verify friend can see BOTH public AND friends-only posts
        public_post_found = False
        friends_post_found = False
        
        for post in friend_response.data.get("posts", []):
            if post.get("title") == "Public Post":
                public_post_found = True
            if post.get("title") == "Friends Only Post":
                friends_post_found = True
        
        self.assertTrue(public_post_found, "Friend should see public posts")
        self.assertTrue(friends_post_found, "Friend should see friends-only posts")
        
        # Now test with non-friend (user3/author3)
        self.client.logout()
        self.client.force_login(self.user3)
        
        # Call API as non-friend
        non_friend_response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        # Check response status
        self.assertEqual(non_friend_response.status_code, 200)
        
        # Non-friend should see public posts but NOT friends-only posts
        public_post_found = False
        friends_post_found = False
        
        for post in non_friend_response.data.get("posts", []):
            if post.get("title") == "Public Post":
                public_post_found = True
            if post.get("title") == "Friends Only Post":
                friends_post_found = True
        
        self.assertTrue(public_post_found, "Non-friend should see public posts")
        self.assertFalse(friends_post_found, "Non-friend should NOT see friends-only posts")
        
        print(f"API friends post visibility test passed")
    
    def test_unlisted_post_visibility(self):
        """Test that UNLISTED posts are only visible with direct link"""
        # test in DB first
        # Should be visible to the author
        own_posts = Post.objects.filter(author=self.author1, visibility="UNLISTED")
        self.assertEqual(own_posts.count(), 1)
        self.assertEqual(own_posts.first().title, "Unlisted Post")
        
        # Should be accessible by direct ID
        post_id = self.unlisted_post.id
        direct_access_post = Post.objects.get(id=post_id)
        self.assertEqual(direct_access_post.title, "Unlisted Post")
        
        # But should not appear in regular listings (simulate this)
        public_stream = Post.objects.filter(visibility="PUBLIC")
        unlisted_in_public = any(p.id == self.unlisted_post.id for p in public_stream)
        self.assertFalse(unlisted_in_public, "Unlisted post should not appear in public stream")
        
        ##################################################################

        author_id = self.author1.id.split('/')[-1]
        post_id = self.unlisted_post.internal_id
        
        # First test general listing - should NOT include unlisted post
        url = reverse("social:api_get_author_and_all_post", kwargs={"id": author_id})
        response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        self.assertEqual(response.status_code, 200)
        
        # Check that unlisted post is NOT in the general listing
        unlisted_post_found = False
        for post in response.data.get("posts", []):
            if post.get("title") == "Unlisted Post":
                unlisted_post_found = True
        
        self.assertFalse(unlisted_post_found, "Unlisted post should not appear in general listing")
        
        # Now test direct access to the unlisted post
        url = reverse("social:get_author_and_post", kwargs={
            "author_id": author_id,
            "internal_id": post_id
        })
        direct_response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        # The post should be accessible directly
        self.assertEqual(direct_response.status_code, 200)
        self.assertEqual(direct_response.data.get("title"), "Unlisted Post")
        
        print(f"API unlisted post access test passed")
    
    def test_post_manager_filters(self):
        """Test the Post.objects manager's filtering capabilities"""
        # Create another post to ensure filtering works properly
        Post.objects.create(
            author=self.author1,
            title="Another Public Post",
            content="This is another public post",
            contentType="text/plain",
            visibility="PUBLIC",
            description="Another public test post"
        )
        
        public_posts = Post.objects.filter(visibility="PUBLIC")
        self.assertEqual(public_posts.count(), 2)
        
        # Get all posts for author1 (should be 4 total)
        all_author_posts = Post.objects.filter(author=self.author1)
        self.assertEqual(all_author_posts.count(), 4)
        
        # Test filtering by content type
        plain_text_posts = Post.objects.filter(contentType="text/plain")
        self.assertEqual(plain_text_posts.count(), 4)
        
        print(f"Post manager filtering test passed")
    
    def test_deleted_post_visibility(self):
        """Test that DELETED posts are not visible"""
        # Create a post and then mark it as deleted
        deleted_post = Post.objects.create(
            author=self.author1,
            title="Soon To Be Deleted Post",
            content="This post will be deleted",
            contentType="text/plain",
            visibility="PUBLIC",
            description="Deleted test post"
        )
        
        # Verify it exists
        self.assertIsNotNone(Post.objects.filter(id=deleted_post.id).first())

        author_id = self.author1.id.split('/')[-1]
        post_id = deleted_post.internal_id
        
        # First verify the post exists and is accessible
        url = reverse("social:get_author_and_post", kwargs={
            "author_id": author_id,
            "internal_id": post_id
        })
        initial_response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(initial_response.data.get("title"), "Soon To Be Deleted Post")

        # Now mark it as deleted by changing visibility
        deleted_post.visibility = "DELETED"
        deleted_post.save()
        
        # Verify it's not included in PUBLIC queries
        public_posts = Post.objects.filter(visibility="PUBLIC")
        deleted_in_public = any(p.id == deleted_post.id for p in public_posts)
        self.assertFalse(deleted_in_public, "Deleted post should not appear in public posts")
        
        # But it should still be accessible directly if you know the ID
        direct_access = Post.objects.get(id=deleted_post.id)
        self.assertEqual(direct_access.visibility, "DELETED")
        
        # Check it's no longer visible in listings
        list_url = reverse("social:api_get_author_and_all_post", kwargs={"id": author_id})
        list_response = self.client.get(list_url, HTTP_HOST="localhost:8000")
        
        self.assertEqual(list_response.status_code, 200)
        
        deleted_post_found = False
        for post in list_response.data.get("posts", []):
            if post.get("title") == "Soon To Be Deleted Post":
                deleted_post_found = True
        
        self.assertFalse(deleted_post_found, "Deleted post should not appear in listing")
        
        # Direct access might return 404 or a post with DELETED visibility depending on your implementation
        direct_response = self.client.get(url, HTTP_HOST="localhost:8000")
        
        # Either it returns 404 or the post has DELETED visibility
        if direct_response.status_code == 404:
            self.assertEqual(direct_response.status_code, 404)
        else:
            self.assertEqual(direct_response.status_code, 200)
            self.assertEqual(direct_response.data.get("visibility"), "DELETED")
        
        print(f"API deleted post visibility test passed")