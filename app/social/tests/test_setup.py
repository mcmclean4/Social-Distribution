from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth.models import User
from social.models import Author

class TestSetUp(APITestCase):
    '''
    re-run app with docker compose build & up
    in another terminal run tests with this command:
    docker exec -it w25-project-mod-cornsilk-socialapp-1 python manage.py test
    '''
    def setUp(self):
        # urls of endpoints from urls.py
        self.posts_url = reverse('social:post_list_create')

         # Create a user for the author
        self.user = User.objects.create_user(username="anonymous_user", password="password")

        # Create an Author instance in the test database
        self.author = Author.objects.create(
            user=self.user,
            id="http://localhost:8000/authors/anonymous_user",
            host="http://localhost:8000",
            displayName="Anonymous Author"
        )

        # Authenticate the test client
        self.client.force_login(self.user)  # Ensures the client is authenticated

        # data for a plain text post
        self.post_data = {
            "type":"Post",
            "title":"A post title about a post about web dev",
            "id":"http://nodebbbb/api/authors/222/posts/249",
            "page": "http://nodebbbb/authors/222/posts/293",
            "description":"This post discusses stuff -- brief",
            "contentType":"text/plain",
            "content":"Þā wæs on burgum Bēowulf Scyldinga",
            "author": self.author.id,
            "published":"2015-03-09T13:07:04+00:00",
            "visibility":"PUBLIC"
        }


        return super().setUp()
    
    def tearDown(self):
        return super().tearDown()