from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.auth.models import User
from .models import Author, Post, Comment, Follow, Node, Like
from django.contrib.admin.views.decorators import staff_member_required
from .views import custom_admin_view
# Register your models here.


class CustomAdminSite(admin.AdminSite):
    site_header = "Social Admin Panel"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('sql/', self.admin_view(custom_admin_view), name='sql'),
        ]
        return custom_urls + urls
    
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        custom_app_label = "Database Management"
        custom_app = None

        for app in app_list:
            if app["name"] == custom_app_label:
                custom_app = app
                break

        if not custom_app:
            custom_app = {"name": custom_app_label, "app_label": "custom_tools", "models": []}
            app_list.append(custom_app)

        # Add the custom link under the chosen app
        custom_app["models"].append({
            "name": "SQL Queries",
            "admin_url": "/admin/sql/",
            "view_only": True,
        })

        return app_list

admin_site = CustomAdminSite(name='custom_admin')

admin_site.register(Author)
admin_site.register(User)
admin_site.register(Post)
admin_site.register(Comment)
admin_site.register(Follow)
admin_site.register(Node)
admin_site.register(Like)