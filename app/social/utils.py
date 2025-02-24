from django.shortcuts import get_object_or_404

from social.models import *


def get_friends(author):
    """
    Return list of author objects that are friends with the given author
    """
    author_id = author.id

    # Find people who mutually follow the given author
    following_ids = set(Follow.objects.filter(follower_id=author_id).values_list("followee_id", flat=True))
    followers_ids = set(Follow.objects.filter(followee_id=author_id).values_list("follower_id", flat=True))
    friends_ids = following_ids.intersection(followers_ids)

    # Get author objects
    friends = []
    for friend in friends_ids:
        friends.append(id_to_author(friend))
    friends.append(author)   # Author is a friend of themselves
    return friends

def id_to_author(id):
    """
    Convert author ID to author object
    """
    return get_object_or_404(Author, id=id)