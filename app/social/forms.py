from django import forms
from .models import Post, Author
from .models import Post
from .models import Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content', 'image', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contentType': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['displayName', 'profileImage']
        widgets={
            'displayName': forms.TextInput(attrs={'class': 'form-control'}),
            'profileImage': forms.ClearableFileInput(attrs={'class': 'form-control'})
            }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }