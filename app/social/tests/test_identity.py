from .test_setup import TestSetUp
from social.models import Author    


class TestIdentity(TestSetUp):
    
    '''
    Identity 1. Successfully create an author with a consistent identity
    '''
    def testCreateAuthor(self):
        # Create author
        response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(response.status_code, 302)
        author = Author.objects.last()
        self.assertIsNotNone(author)
        self.assertEqual(author.displayName, self.register_data['displayName'])

        # Now repeat with same user registration data to ensure usernames are unique
        response = self.client.post(
            self.register_url, self.register_data)
        # Expect a bad request
        self.assertEqual(response.status_code, 400)

        # Now repeat with a second user's registration data to ensure unique ids
        response = self.client.post(
            self.register_url, self.register_data_2)
        # Expect a redirect
        self.assertEqual(response.status_code, 302)
        author_2 = Author.objects.last()
        self.assertIsNotNone(author_2)
        self.assertEqual(author_2.displayName, self.register_data_2['displayName'])
        # Check this second author has a different id
        self.assertNotEqual(author.id, author_2.id)

        


        