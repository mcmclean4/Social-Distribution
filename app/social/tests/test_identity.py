from .test_setup import TestSetUp
from social.models import Author    


class TestIdentity(TestSetUp):
    
    '''
    Identity 1. Successfully create an author with a consistent identity
    '''
    def testCreateAuthor(self):
        # Create author
        post_response = self.client.post(
            self.register_url, self.register_data)
        # Expect a redirect
        self.assertEqual(post_response.status_code, 302)

        # Now get the author's id and retrieve it from /api/authors/{AUTHOR_SERIAL}/ endpoint
        # Using .last() since test_setup.py already creatd a separate Author manually, which is only used in other test files
        author_id = Author.objects.last().id
        get_response = self.client.get(
            author_id
        )
        # Check id is the same and displayName is same as what was registered with
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data['id'], author_id)
        self.assertEqual(get_response.data['displayName'], self.register_data['displayName'])


    '''
    Identity 2. Successfully create multiple authors
    '''
    def testCreateMultipleAuthors(self):
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


        


        