from .test_setup import TestSetUp
from social.models import Author
import base64    


class TestIdentity(TestSetUp):
    
    '''
    Identity 1. Successfully create an author with a consistent identity
    '''
    def test_create_author(self):
        # Create author
        post_response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(post_response.status_code, 302)

        # Now get the author's id and retrieve it from /api/authors/{AUTHOR_SERIAL}/ endpoint
        # Using .last() since test_setup.py already creatd a separate Author manually, which is only used in other test files
        author_id = Author.objects.last().id

        # auth header for django test client
        auth_str = f"{self.node.auth_username}:{self.node.auth_password}"
        auth_header = f"Basic {base64.b64encode(auth_str.encode()).decode()}"

        get_response = self.client.get(
            author_id,
            HTTP_AUTHORIZATION=auth_header
        )
        # Check id is the same and displayName is same as what was registered with
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data['id'], author_id)
        self.assertEqual(get_response.data['displayName'], self.register_data['displayName'])


    '''
    Identity 2. Successfully create multiple authors
    '''
    def test_create_multiple_authors(self):
        # Create author
        response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(response.status_code, 302)
        author_1 = Author.objects.last()
        get_response_1 = self.client.get(
            author_1.id
        )
        self.assertEqual(get_response_1.status_code, 200)

        # Now repeat with a second user's registration data
        response = self.client.post(
            self.register_url, self.register_data_2)
        # Expect a redirect
        self.assertEqual(response.status_code, 302)
        author_2 = Author.objects.last()
        get_response_2 = self.client.get(
            author_2.id
        )
        self.assertEqual(get_response_2.status_code, 200)

        # Check this second author has a different id
        self.assertNotEqual(author_1.id, author_2.id)
        self.assertNotEqual(get_response_1.data['displayName'], get_response_2.data['displayName'])

        # Use /api/authors/ endpoint to check there's multiple authors
        get_response_all = self.client.get(
            self.get_authors_url
        )
        self.assertEqual(get_response_all.status_code, 200)
        
        # Skip [0] since its the manually created Author in setup
        # Check the 2 Authors we created are present in the list of all Authors
        self.assertEqual(get_response_all.data[1]['id'], author_1.id)
        self.assertEqual(get_response_all.data[2]['id'], author_2.id)
    
    
    '''
    Identity 3. Successfully create public profile page for an author
    '''
    def test_profile_information(self):
        # Create author
        post_response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(post_response.status_code, 302)

        # Now get the author's public page with profile information
        get_response = self.client.get(
            self.profile_page_url(1)
        )
        # Check author's information is displayed on their page
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/profile.html')
        self.assertContains(get_response, self.author.displayName)


    '''
    Identity . Successfully show author's posts on their profile page
    '''
    def test_profile_posts(self):
        # Create author
        post_response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(post_response.status_code, 302)

        # Create a post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        # Now get the author's public page with profile information
        get_response = self.client.get(
            self.profile_page_url(1)
        )
        # Check profile page is served
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/profile.html')
        # Check author's post is displayed on their page
        self.assertContains(get_response,  self.plaintext_post_data['title'])
        self.assertContains(get_response,  self.plaintext_post_data['content'])


    '''
    Identity 6. Successfully show author's posts on their profile page
    '''
    def test_edit_profile(self):
        # Create author
        post_response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(post_response.status_code, 302)
        author_id = Author.objects.last().id

        # Update the author's display name and subumit the form
        new_display_name = "Updated Author Name"
        form_data = {
            "displayName": new_display_name,
            "profileImage": "images/default_profile.png"
        }
        post_edit_response = self.client.post(self.profile_edit_url(2), form_data, follow=True)
        # Expect a redirect to the profile page
        self.assertRedirects(post_edit_response, self.profile_page_url(2))
        # use api to check the author's name has been updated
        get_response = self.client.get(
            author_id
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data['id'], author_id)
        self.assertEqual(get_response.data['displayName'], new_display_name)


        