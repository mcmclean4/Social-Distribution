import requests
from django.shortcuts import redirect
from django.conf import settings
import urllib.parse
import uuid
from datetime import datetime, timezone
from .models import Post

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
    return redirect(url)


def github_callback(request):
    '''Handles callback after the user has granted github permissions'''

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

    # Store the access token in the user's session
    request.session["github_access_token"] = access_token
    # Redirect the user to the stream view
    return redirect("social:index")

def fetch_user_activity(request):
    ''' Checks if the current user has any recent github activity that should generate new posts'''

    username = request.user.author.github
    access_token = request.session.get("github_access_token")
    if not access_token:
        print("no access token")
        return None  # The user needs to authorize the app first

    url = f"https://api.github.com/users/{username}/events/public"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        # Successfully retrieved list of github events, create posts for them if needed
        # print(response.json()) # debugging
        generate_new_posts(response.json(), request.user.author)
    elif response.status_code == 401:
        # Token is invalid (expired or revoked)
        print("Token is invalid; redirecting to reauthorize")
        request.session.pop("github_access_token", None)  # Clear the invalid token
        return "invalid_token"  # Indicate that the token is invalid so that we can redirect to the authorization url
    else:
        print(f"Error fetching user activity: {response.status_code} - {response.text}")
        return None
    
def generate_new_posts(events, author):
    ''' Takes list of github events, creates a post for any event more recent than the author's github_activity timestamp'''
    
    created_new_post = False
    last_updated = author.github_timestamp
    # print(events[0])
    print(f"last_updated: {last_updated}")
    
    for event in events:
        event_time = datetime.fromisoformat(event['created_at'].replace("Z", "+00:00"))
        print(f"event_time: {event_time}")
        # Only create posts for events that are more recent than the last time we fetched activity for this author
        if (last_updated > event_time):
            break
        
        # Create a post for the event
        event_titles = {
            "CommitCommentEvent": "commented on a commit in the repository",
            "CreateEvent": "created a new branch or tag in the repository",
            "DeleteEvent": "deleted a branch or tag in the repository",
            "ForkEvent": "forked the repository",
            "GollumEvent": "created or updated a wiki page in the repository",  
            "IssueCommentEvent": "commented on an issue in the repository",
            "IssuesEvent": "opened, closed, or updated an issue in the repository",
            "MemberEvent": "added or removed a collaborator in the repository",
            "PublicEvent": "made the repository public",
            "PullRequestEvent": "opened, closed, or updated a pull request in the repository",
            "PullRequestReviewEvent": "reviewed a pull request in the repository",
            "PullRequestReviewCommentEvent": "commented on a pull request review in the repository",
            "PullRequestReviewThreadEvent": "marked a comment thread on a pull request in the repository", 
            "PushEvent": "pushed commits to the repository",
            "ReleaseEvent": "published a release in the repository",
            "SponsorshipEvent": "created a sponsorship in the repository",  
            "WatchEvent": "starred the repository",
        }

        # Default title for some unspecified event type (shouldn't ever happen)
        title = f'{event['actor']['login']} performed some action in {event['repo']['name']}'
        if event['type'] in event_titles:
            title = f'{event['actor']['login']} {event_titles[event['type']]} {event['repo']['name']}'

        # Create and save the Post object
        post = Post(
            title=title,
            description="GitHub Activity",
            contentType="text/plain",
            content=f"This post was generated automatically for {author.displayName}'s GitHub activity.",
            author=author,
            visibility="PUBLIC",
        )
        post.save()
        created_new_post = True

    # Only update current time when we've created new posts, since github api takes a year to update
    if created_new_post:
        author.github_timestamp = datetime.now(timezone.utc)
        author.save()





