import base64
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from django.conf import settings
from social.models import Node, Author, Inbox, Post
from unittest.mock import MagicMock, patch


class NodeAPITests(TestCase):
    def setUp(self):
        # Set the HOST as used in our models/URLs.
        settings.HOST = "http://localhost:8000/social/"

        # Create a local admin user to manage nodes.
        self.admin_user = User.objects.create_superuser(
            username="admin", password="adminpass", email="admin@example.com"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin_user)

        # Create a remote node already in the system to test listing and auth.
        self.remote_node = Node.objects.create(
            name="TestRemoteNode",
            base_url="http://remotenode.com/api/",
            auth_username="remotetest",
            auth_password="remotepass",  # In production, store a hashed version.
            enabled=True
        )
        # Prepare valid and invalid HTTP Basic Auth headers for remote requests.
        valid_credentials = base64.b64encode(b"remotetest:remotepass").decode("utf-8")
        self.valid_remote_header = "Basic " + valid_credentials
        invalid_credentials = base64.b64encode(b"wrong:creds").decode("utf-8")
        self.invalid_remote_header = "Basic " + invalid_credentials

    def test_create_node(self):
        """
        As a node admin, I want to be able to connect to remote nodes by entering only the URL,
        a username, and a password. This tests adding a node via the RESTful interface.
        """
        url = reverse("node_create")  # Expected URL for creating a Node.
        data = {
            "name": "New Remote Node",
            "base_url": "http://newremote.com/api/",
            "auth_username": "newuser",
            "auth_password": "newpass"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "New Remote Node")
        self.assertEqual(response.data["base_url"], "http://newremote.com/api/")
        # Ensure auth_password is not returned (write_only)
        self.assertNotIn("auth_password", response.data)
        self.assertTrue(Node.objects.filter(base_url="http://newremote.com/api/").exists())

    def test_list_nodes(self):
        """
        As a node admin, I want a RESTful interface for most operations so that I can view
        connected remote nodes.
        """
        url = reverse("node_list")  # Expected URL to list nodes.
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Assuming response is a list of nodes.
        node_ids = [str(node["id"]) for node in response.data]
        self.assertIn(str(self.remote_node.id), node_ids)

    def test_delete_node(self):
        """
        As a node admin, I want to be able to remove nodes and stop sharing with them.
        """
        node_to_delete = Node.objects.create(
            name="DeleteMe",
            base_url="http://deletenode.com/api/",
            auth_username="deleteuser",
            auth_password="deletepass",
            enabled=True
        )
        url = reverse("node_detail", kwargs={"pk": node_to_delete.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Node.objects.filter(pk=node_to_delete.pk).exists())

    def test_remote_node_authentication_valid(self):
        """
        As a node admin, node-to-node connections can be authenticated with HTTP Basic Auth.
        Test that a remote node with valid credentials is allowed to access a protected endpoint.
        """
        # Create a dummy local author to target.
        dummy_user = User.objects.create_user(username="dummy", password="dummy")
        dummy_author = Author.objects.create(
            user=dummy_user,
            displayName="Dummy Author",
            host="http://localhost:8000/social/api/",
            github="",
            profileImage=None,
            page="http://localhost:8000/social/authors/dummy"
        )
        tail_id = dummy_author.id.split("/")[-1]
        inbox_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        # Set client credentials to valid remote header.
        self.client.credentials(HTTP_AUTHORIZATION=self.valid_remote_header)
        response = self.client.get(inbox_url)
        self.assertEqual(response.status_code, 200)

    def test_remote_node_authentication_invalid(self):
        """
        As a node admin, I can prevent nodes from connecting to my node if they don't have
        a valid username and password.
        Test that an invalid remote node is rejected.
        """
        dummy_user = User.objects.create_user(username="dummy2", password="dummy")
        dummy_author = Author.objects.create(
            user=dummy_user,
            displayName="Dummy Author 2",
            host="http://localhost:8000/social/api/",
            github="",
            profileImage=None,
            page="http://localhost:8000/social/authors/dummy2"
        )
        tail_id = dummy_author.id.split("/")[-1]
        inbox_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        self.client.credentials(HTTP_AUTHORIZATION=self.invalid_remote_header)
        response = self.client.get(inbox_url)
        self.assertEqual(response.status_code, 401)

    def test_disable_node_interface(self):
        """
        As a node admin, I can disable the node-to-node interfaces for connections that I no longer want.
        Test that when a node is disabled, its subsequent requests are rejected.
        """
        # Disable the remote node.
        self.remote_node.enabled = False
        self.remote_node.save()

        dummy_user = User.objects.create_user(username="dummy3", password="dummy")
        dummy_author = Author.objects.create(
            user=dummy_user,
            displayName="Dummy Author 3",
            host="http://localhost:8000/social/api/",
            github="",
            profileImage=None,
            page="http://localhost:8000/social/authors/dummy3"
        )
        tail_id = dummy_author.id.split("/")[-1]
        inbox_url = reverse("social:api_inbox", kwargs={"author_id": tail_id})
        # Even with valid credentials, the disabled node should be rejected.
        self.client.credentials(HTTP_AUTHORIZATION=self.valid_remote_header)
        response = self.client.get(inbox_url)
        self.assertEqual(response.status_code, 401)  # or 403, based on your implementation

    def test_restful_interface_for_nodes(self):
        """
        As a node admin, I want a RESTful interface for most operations.
        This test covers creating, retrieving, updating, and deleting a remote node.
        """
        # Create a new node.
        create_url = reverse("node_create")
        data = {
            "name": "Restful Node",
            "base_url": "http://restfulnode.com/api/",
            "auth_username": "restuser",
            "auth_password": "restpass"
        }
        create_response = self.client.post(create_url, data, format="json")
        self.assertEqual(create_response.status_code, 201)

        # Retrieve list and ensure the new node is present.
        list_url = reverse("node_list")
        list_response = self.client.get(list_url)
        self.assertEqual(list_response.status_code, 200)
        node_ids = [str(node["id"]) for node in list_response.data]
        new_node_id = str(create_response.data["id"])
        self.assertIn(new_node_id, node_ids)

        # (Optionally) Update the node via a PATCH or PUT request.
        update_url = reverse("node_detail", kwargs={"pk": new_node_id})
        update_data = {"name": "Restful Node Updated"}
        update_response = self.client.patch(update_url, update_data, format="json")
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.data["name"], "Restful Node Updated")

        # Finally, delete the node.
        delete_response = self.client.delete(update_url)
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Node.objects.filter(pk=new_node_id).exists())
