import requests
from django.shortcuts import redirect
from django.conf import settings
import urllib.parse

def github_authorize(request):
    # Redirect the user to GitHub's authorization page
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_CALLBACK_URL,
        "scope": "public_repo,user",  # Request access to public repos and user data
        "state": "random_string",  # Optional: Add a state parameter for security
    }
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    return redirect(url)


def github_callback(request):
    # Get the temporary code from the callback
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Exchange the code for a user access token
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_CALLBACK_URL,
        },
    )
    token_data = response.json()
    access_token = token_data.get("access_token")

    # Store the access token (e.g., in the user's session or database)
    request.session["github_access_token"] = access_token

    # Redirect the user to a success page
    return redirect("social:index")

def fetch_user_activity(request, username):
    access_token = request.session.get("github_access_token")
    if not access_token:
        print("no access token")
        return None

    url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching user activity: {response.status_code} - {response.text}")
        return None

