from .test_setup import TestSetUp
from social.models import Post

class TestPosting(TestSetUp):
    '''
    Add these lines before the assertions, and write response.data into terminal after running for debugging
    import pdb
    pdb.set_trace()
    '''

    '''
    Posting 1 & 6. Successfully create a plain text post
    '''
    def testCreatePlaintextPost(self):
        # Create post
        response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        # Check response status code and data fields are same as the post that we created
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

        post_auto_id = create_response.data['auto_id']

        # Make changes to some fields
        self.plaintext_post_data['title'] = "An Updated Title"
        self.plaintext_post_data['description'] = "An updated description"
        self.plaintext_post_data['contentType'] = "text/markdown"
        self.plaintext_post_data['content'] = "Updated content"

        # Submit the changes as a form with POST request
        update_response = self.client.post(
            self.post_update_url(post_auto_id), self.plaintext_post_data)
        self.assertEqual(update_response.status_code, 302)

        # Get post from db and check all the updated fields are correct and has kept the same auto_id
        post = Post.objects.first()
        self.assertEqual(post.title, self.plaintext_post_data['title'])
        self.assertEqual(post.description, self.plaintext_post_data['description'])
        self.assertEqual(post.contentType, self.plaintext_post_data['contentType'])
        self.assertEqual(post.content, self.plaintext_post_data['content'])


    '''
    Posting 5 & 8. Successfully create a markdown text post
    '''
    def testCreateMarkdownPost(self):
        response = self.client.post(
            self.posts_url, self.markdown_post_data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['contentType'], self.markdown_post_data['contentType'])
        self.assertEqual(response.data['content'], self.markdown_post_data['content'])


    '''
    Posting 7. Successfully create a markdown text post
    '''
    def testCreateImagePost(self):
        response = self.client.post(
            self.posts_url, self.image_post_data, format="multipart")  # Use multipart for images
        self.assertEqual(response.status_code, 201)

        # Check if image is included in response, and should return as a url
        self.assertIn("image", response.data)
        self.assertTrue(response.data["image"].startswith("http"))

        # Ensure other fields are correctly saved
        self.assertEqual(response.data["title"], self.image_post_data["title"])
        self.assertEqual(response.data["description"], self.image_post_data["description"])
        self.assertEqual(response.data["contentType"], self.image_post_data["contentType"])


    '''
    Posting 9. Successfully delete a post by updating its visibility field
    '''
    def testDeletePost(self):
        # Create post with visibility:"PUBLIC"
        create_response = self.client.post(
            self.posts_url, self.plaintext_post_data, format="json")
        self.assertEqual(create_response.status_code, 201)

        post_auto_id = create_response.data['auto_id']

        delete_response = self.client.post(
            self.post_delete_url(post_auto_id), self.plaintext_post_data, format="json")
        # Expect to be redirected to social/index/ after a successful deletion
        self.assertEqual(delete_response.status_code, 302)

        # Get post from db and check the visibility field is updated correctly
        post = Post.objects.first()
        self.assertEqual(post.visibility, "DELETED")


    '''
    Posting 10. Successfully create a post through the web browser
    '''
    def testCreatePostViaBrowser(self):
        # Visit the create post page
        visit_response = self.client.get(self.post_create_url)
        self.assertEqual(visit_response.status_code, 200)
        self.assertTemplateUsed(visit_response, 'social/create_post.html')
        
        # Submit the plaintext post as a form with POST request
        submit_response = self.client.post(self.post_create_url, self.plaintext_post_data)
        self.assertEqual(submit_response.status_code, 302)

        # Verify that the post was created in the database
        post = Post.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.title, self.plaintext_post_data['title'])
        self.assertEqual(post.content, self.plaintext_post_data['content'])
        self.assertEqual(post.author, self.author)


