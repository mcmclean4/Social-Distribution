'''
Used by locust service to load test API endpoints.
'''

from locust import HttpUser, task, between
import random

class QuickstartUser(HttpUser):
    wait_time = between(1, 5)  # Simulate user think time between tasks.
    username = "PiceaGlauca"
    password = "12345678"

    def on_start(self):
        """
        Logs the user in using the credentials provided during registration.
        """
        data = {
            "username": self.username,
            "password": self.password,
        }
        with self.client.post("/social/login/", data=data, catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")

    @task(2)
    def get_stream(self):
        """
        GET the stream page (/social/index).
        """
        self.client.get("/social/index")

    @task(2)
    def get_my_posts(self):
        """
        GET the my posts page (/social/my_posts).
        """
        self.client.get("/social/my_posts")

