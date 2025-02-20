from .test_setup import TestSetUp

class TestViews(TestSetUp):
    '''
    Add these lines before the assertions, and write response.data into terminal after running for debugging
    import pdb
    pdb.set_trace()

    '''
    '''
    Posting 1 & 6. Successfully create a plain text post
    '''
    def testCreatePlaintextPost(self):
        response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['contentType'], self.plaintext_post_data['contentType'])
        self.assertEqual(response.data['content'], self.plaintext_post_data['content'])

    '''
    Posting 3. Successfully update an exisitng post
    '''
    def testEditPost(self):
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        post_id = create_response.data['auto_id']

        # Update fields
        self.plaintext_post_data['title'] = "An Updated Title"
        self.plaintext_post_data['description'] = "An updated description"
        self.plaintext_post_data['contentType'] = "text/markdown"
        self.plaintext_post_data['content'] = "Updated content"

        update_response = self.client.post(
            self.post_update_url(post_id), self.plaintext_post_data, format="json")
        self.assertEqual(update_response.status_code, 200)

        '''
        Might need update to return post objects in body to verify fields are actually updated
        # Check all the updated fields are correct
        self.assertEqual(update_response.data['title'], self.plaintext_post_data['title'])
        self.assertEqual(update_response.data['description'], self.plaintext_post_data['description'])
        self.assertEqual(update_response.data['contentType'], self.plaintext_post_data['contentType'])
        self.assertEqual(update_response.data['content'], self.plaintext_post_data['content'])
        # Check the post has kept the same id after updating
        self.assertEqual(create_response.data['id'], self.plaintext_post_data['id'])
        '''
        
    '''
    Posting 5. Successfully create a markdown text post
    '''
    def testCreateMarkdownPost(self):
        response = self.client.post(
            self.posts_url, self.markdown_post_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['contentType'], self.markdown_post_data['contentType'])
        self.assertEqual(response.data['content'], self.markdown_post_data['content'])