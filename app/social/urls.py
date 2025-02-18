from django.urls import path
from . import views

app_name = 'social'
urlpatterns = [
    #
    path("", views.stream, name="stream"),
    # API paths
    path("api/<str:pk>/", name="author")    # Sample api path for your feature

]