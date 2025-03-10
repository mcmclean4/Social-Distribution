from .test_setup import TestSetUp

class TestReading(TestSetUp):

    '''
    Reading 1a & 2. Stream page successfully shows all public posts, with the most recent first
    '''
    def test_stream(self):
        # Create first post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

         # Create a second post
        create_response = self.client.post(
            self.posts_url, self.markdown_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        get_response = self.client.get(
            self.posts_url
        )
        # Check we can get all posts through the api with a get request, the first object being the newest markdown post
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(get_response.data[0]['contentType'], self.markdown_post_data['contentType'])
        self.assertEqual(get_response.data[1]['contentType'], self.plaintext_post_data['contentType'])

        # Get the stream page
        get_response = self.client.get(
            self.stream_url
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/index.html')
        # Check stream display all posts
        self.assertContains(get_response,  self.plaintext_post_data['title'])
        self.assertContains(get_response,  self.markdown_post_data['title'])

        # Ensure the newest markdown post appears before the plaintext post in the response content
        response_content = get_response.content.decode()
        markdown_index = response_content.find(self.markdown_post_data['title'])
        plaintext_index = response_content.find(self.plaintext_post_data['title'])
        self.assertTrue(markdown_index < plaintext_index, "Newest post is not appearing first in the stream.")

    
    
    '''
    Reading 1c. Stream page shows updated versions of posts
    '''
    def test_stream_edit(self):
        # Create a post
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        parts = create_response.data['id'].split('/')
        author_serial = int(parts[-3])
        post_serial = int(parts[-1]) 

        # Make changes to some fields
        self.plaintext_post_data['title'] = "An Updated Title"
        self.plaintext_post_data['description'] = "An updated description"

        # Submit the changes with PUT request
        update_response = self.client.put(
            self.post_general_url(author_serial, post_serial), self.plaintext_post_data, format="json")
        self.assertEqual(update_response.status_code, 200)

        # Get the stream page
        get_response = self.client.get(
            self.stream_url
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/index.html')
        # Check stream displays the updated fields
        self.assertContains(get_response,  self.plaintext_post_data['title'])
        self.assertContains(get_response,  self.plaintext_post_data['description'])

    
    '''
    Reading 1d. Stream page does not show deleted posts
    '''
    def test_stream_delete(self):
        # Create a post with deleted visibility
        self.plaintext_post_data['visibility'] = "DELETED"
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        # Get the stream page
        get_response = self.client.get(
            self.stream_url
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertTemplateUsed(get_response, 'social/index.html')
        # Check stream does not display the post's fields
        self.assertNotContains(get_response,  self.plaintext_post_data['title'])
        self.assertNotContains(get_response,  self.plaintext_post_data['description'])