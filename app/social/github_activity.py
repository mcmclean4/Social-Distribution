import requests
from django.shortcuts import redirect
from django.conf import settings
import urllib.parse
import uuid

def github_authorize(request):
    '''Redirects the user to GitHub's authorization page to request read permission for github user events'''
    state = str(uuid.uuid4()) # random state parameter string for security
    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": settings.GITHUB_CALLBACK_URL,
        "scope": "public_repo,user",  # Request access to public repos and user data
        "state": state,  
    }
    
    url = f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"
    print(f"going to url: {url}")
    return redirect(url)


def github_callback(request):
    '''Handles callback after the user has granted github permissions'''
    code = request.GET.get("code")
    state = request.GET.get("state")
    print('handling callback')

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

    print(f"access token in callback func: {access_token}")

    # Store the access token in the user's session
    request.session["github_access_token"] = access_token

    # Redirect the user to the stream view
    return redirect("social:index")

def fetch_user_activity(request, username):

    ''' Checks if the current user has any recent github activity that should generate new posts'''

    access_token = request.session.get("github_access_token")
    if not access_token:
        print("no access token")
        return None  # The user needs to authorize the app first
    
    print(f"access token in fetch: {access_token}")

    url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        # Token is invalid (expired or revoked)
        print("Token is invalid; redirecting to reauthorize")
        request.session.pop("github_access_token", None)  # Clear the invalid token
        return "invalid_token"  # Indicate that the token is invalid so that we can redirect to the authorization url
    else:
        print(f"Error fetching user activity: {response.status_code} - {response.text}")
        return None

