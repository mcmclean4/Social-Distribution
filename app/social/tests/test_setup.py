from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.models import User
from social.models import Author
from django.core.files.uploadedfile import SimpleUploadedFile
import io
from PIL import Image 

# Referenced:
# https://www.youtube.com/watch?v=17KdirMbmHY
# 

class TestSetUp(APITestCase):
    '''
    re-run app with docker compose build & up
    in another terminal run tests with this command in app/:
    docker exec -it w25-project-mod-cornsilk-socialapp-1 python manage.py test social.tests

    or if you only want to run one of the test files (test_sharing in this example) use:
    docker exec -it w25-project-mod-cornsilk-socialapp-1 python manage.py test social.tests.test_sharing


    '''
    def setUp(self):

        # Create a user for the author
        self.user = User.objects.create_user(username="test_user", password="password")
        # Authenticate the test client
        self.client.force_login(self.user)

        self.setUpIdentity()

        # ** EVERYTHING BELOW WAS MADE FOR TEST_POSTING.PY **
        # So may or may not need everything for other test files.

        # urls of endpoints from urls.py
        self.posts_url = reverse('social:post_list_create')
        # inlcude auto_id argument for paths with variable
        self.post_update_url = lambda post_id: reverse('social:update_post', kwargs={'auto_id': post_id})
        self.post_detail_url = lambda post_id: reverse('social:post_detail', kwargs={'auto_id': post_id})
        self.post_delete_url = lambda post_id: reverse('social:delete_post', kwargs={'auto_id': post_id})
        self.post_create_url = reverse('social:create_post')
        
        # Create an Author instance in the test database
        self.author = Author.objects.create(
            user=self.user,
            id="http://example.com",
            host="http://localhost:8000/social/api/",
            displayName="Test Author"
        )
        self.author.save()

        # Create a test image in memory
        self.image = self.generate_test_image()

        # data for a plain text post
        self.plaintext_post_data = {
            "type": "post",
            "title":"A post title about a post about web dev",
            "id":"http://example.com",
            "page": "http://example.com/profile",
            "title":"A post title about a post about web dev",
            "description":"This post discusses stuff -- brief",
            "contentType": "text/plain",
            "content": "Þā wæs on burgum Bēowulf Scyldinga",
            "author": {
                "type": "author",
                "id": "http://example.com",
                "host": "http://nodeaaaa/api/",
                "displayName": "Test Author",
                "github": "http://github.com/testuser",
                "profileImage": "http://example.com/profile.jpg",
                "page": "http://example.com/profile",
                "isAdmin": False
            },
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC",
            "likes": [],
            "comments": []
        }

        # data for a CommonMark post
        self.markdown_post_data = {
            "type":"Post",
            "title":"A post title about a post about web dev",
            "id":"http://nodebbbb/api/authors/222/posts/249",
            "page": "http://nodebbbb/authors/222/posts/293",
            "description":"This post discusses stuff -- brief",
            "contentType":"text/markdown",
            "content":"**Bold text** ![Sonny and Mariel high fiving.](https://content.codecademy.com/courses/learn-cpp/community-challenge/highfive.gif)",
            "author": self.author.id,
            "published":"2015-03-09T13:07:04+00:00",
            "visibility":"PUBLIC"
        }

        # data for a post with an image
        self.image_post_data = {
            "type": "Post",
            "title": "A post with an image",
            "id": "http://nodebbbb/api/authors/222/posts/250",
            "page": "http://nodebbbb/authors/222/posts/294",
            "description": "This post contains an image",
            "contentType": "image/png;base64", 
            "content":"placeholder content", 
            "image": self.image, 
            "author": self.author.id,
            "published": "2015-03-09T13:07:04+00:00",
            "visibility": "PUBLIC"
        }


        return super().setUp()
    
    def setUpIdentity(self):

        self.register_url = reverse('social:register')

        # Set up needed for test_indentity.py
        self.register_data = {
            "username":"test_username",
            "password": "password",
            "displayName": "test_displayName"
        }

        self.register_data_2 = {
            "username":"test_username2",
            "password": "password2",
            "displayName": "test_displayName2"
        }
    
    def tearDown(self):
        return super().tearDown()
    

    def generate_test_image(self):
        # Generates a simple test png image
        image = io.BytesIO()
        img = Image.new("RGB", (100, 100), color=(255, 0, 0))  # Create a red image
        img.save(image, format="PNG")
        image.seek(0)
        return SimpleUploadedFile("test_image.png", image.getvalue(), content_type="image/png")