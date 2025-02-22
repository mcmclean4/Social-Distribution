from rest_framework import serializers
from .models import Post, Author, User
from .models import Follow

class AuthorSerializer(serializers.Serializer):
    user = User
    type = serializers.CharField(required=True)
    id = serializers.URLField(required=True)
    # host = serializers.URLField(required=True)
    displayName = serializers.CharField(required=True)
    github = serializers.URLField()
    profileImage = serializers.URLField()
    page = serializers.URLField()
    isAdmin = serializers.BooleanField()

    def create(self, validated_data):
        return Author.objects.create(**validated_data)

    def edit(self, validated_data):
        pass


class CommentSerializer(serializers.Serializer):
    id = serializers.URLField()
    author = AuthorSerializer()
    comment = serializers.CharField()
    contentType = serializers.CharField()
    published = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")
    post = serializers.URLField()
    page = serializers.URLField()


class PostLikeSerializer(serializers.Serializer):
    id = serializers.URLField()
    author = AuthorSerializer()
    published = serializers.DateTimeField(format="%Y-%m-%dT%H:%M:%S%z")
    object = serializers.URLField()


class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['id', 'type', 'title', 'description', 'contentType', 'content', 'image', 'author', 'published', 'visibility', 'likes', 'comments']



class FollowRequestSerializer(serializers.ModelSerializer):
    """
    Serializes follow requests into the required format for sending to remote nodes' inboxes.
    """
    type = serializers.CharField(default="follow", read_only=True)
    summary = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = ["type", "summary", "actor", "object"]

    def get_summary(self, obj) -> str:
        """
        Generates the summary message for the follow request.
        """
        return f"{obj.follower.displayName} wants to follow {obj.followee.displayName}"

    def get_actor(self, obj) -> dict:
        """
        Returns the serialized representation of the follower (the one sending the request).
        """
        follower = obj.follower
        return {
            "type": "author",
            "id": follower.id,
            "host": follower.host,
            "displayName": follower.displayName,
            "github": follower.github or "",  # Handle possible null values
            "profileImage": follower.profileImage or "",
            "page": follower.page or "",
        }

    def get_object(self, obj) -> dict:
        """
        Returns the serialized representation of the followee (the recipient of the request).
        """
        followee = obj.followee
        return {
            "type": "author",
            "id": followee.id,
            "host": followee.host,
            "displayName": followee.displayName,
            "github": followee.github or "",
            "profileImage": followee.profileImage or "",
            "page": followee.page or "",
        }
