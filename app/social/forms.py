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
    video = forms.FileField(required=False, help_text="Upload a video (MP4, WebM, max 50MB)")
    class Meta:
        model = Post
        fields = ['title', 'description', 'contentType', 'content', 'visibility']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'contentType': forms.Select(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'visibility': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make content field not required at the form level
        # We'll handle validation in clean()
        self.fields['content'].required = False        

    def clean(self):
        cleaned_data = super().clean()
        content_type = cleaned_data.get('contentType', '')
        content = cleaned_data.get('content', '')

        # Get files from self.files to handle file inputs
        image = self.files.get('image')
        video = self.files.get('video')

        print(f"Clean method - Content type: {content_type}")
        print(f"Clean method - Content present: {bool(content)}")
        print(f"Clean method - Image present: {bool(image)}")
        print(f"Clean method - Video present: {bool(video)}")

        # For text content types, require content field
        if content_type.startswith('text/') and not content:
            print("Content required for text content type")
            self.add_error('content', 'This field is required for text content types.')

        # For image content types, require image file
        elif (content_type.startswith('image/') or content_type == 'application/base64') and not image:
            print("Image required for image content type")
            self.add_error('image', 'An image file is required for image content types.')

        # For video content types, require video file
        elif content_type.startswith('video/') and not video:
            print("Video required for video content type")
            self.add_error('video', 'A video file is required for video content types.')
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