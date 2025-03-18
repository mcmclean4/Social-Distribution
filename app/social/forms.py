from django import forms
from .models import Post, Author
from .models import Comment
from django.core.exceptions import ValidationError
import re
import base64
from io import BytesIO
from PIL import Image

class PostForm(forms.ModelForm):
    image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'contentType': forms.Select(attrs={'class': 'form-select'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'required': False}),  # Remove required attribute
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude 'DELETED' from the visibility choices
        self.fields['visibility'].choices = [choice for choice in Post.CONTENT_VISIBILITY_CHOICES if choice[0] != 'DELETED']
        self.fields['image'].help_text = "Upload an image if content type is an image format."
        # Make content not required at the form level
        self.fields['content'].required = False

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('contentType')
        content = cleaned_data.get('content')
        
        # Validate based on content type
        if content_type in ['image/png;base64', 'image/jpeg;base64', 'application/base64']:
            if self.data and not self.files.get('image'):
                self.add_error('image', 'Please upload an image for this content type.')
        else:
            # Only require content for text content types
            if not content:
                self.add_error('content', 'This field is required for text content types.')
        
        return cleaned_data
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = Author
        fields = ['displayName', 'profileImage']
        
    def clean_profileImage(self):
        profile_image_url = self.cleaned_data.get('profileImage')
        
        # Check if the URL ends with .jpeg or .png
        if profile_image_url:
            if not re.match(r'^https?://.*\.(jpeg|jpg|png)$', profile_image_url, re.IGNORECASE):
                raise forms.ValidationError("Please provide a valid image URL (ending in .jpeg, .jpg, or .png).")
        
        return profile_image_url
    
    def clean_displayName(self):
        display_name = self.cleaned_data['displayName']
        # Check if displayName is already taken
        if Author.objects.filter(displayName=display_name).exclude(id=self.instance.id).exists():
            raise forms.ValidationError("This display name is already taken. Please choose another one.")
        return display_name

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment', 'contentType'] 
        
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'contentType': forms.Select(attrs={'class': 'form-control'}),
        }

class RegisterForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    displayName = forms.CharField(max_length=100)
    github = forms.CharField(required=False)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise ValidationError("The two password fields must match.")

        return cleaned_data