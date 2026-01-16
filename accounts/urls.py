from django.urls import path

from . import views

urlpatterns = [
    path("", views.api_root, name="api_root"),
    path("auth/register", views.register, name="register"),
    path("auth/login", views.login_view, name="login"),
    path("auth/logout", views.logout_view, name="logout"),
    path("users/me", views.me, name="me"),
    path("users/me/delete", views.delete_me, name="delete_me"),
    path("admin/permissions", views.admin_permissions_list, name="admin_permissions_list"),
    path("admin/permissions/create", views.admin_permissions_create, name="admin_permissions_create"),
    path("admin/permissions/<int:rule_id>", views.admin_permissions_delete, name="admin_permissions_delete"),
    path("admin/users/<int:user_id>/roles", views.admin_assign_role, name="admin_assign_role"),
    path("business/projects", views.projects_list, name="projects_list"),
    path("business/reports", views.reports_list, name="reports_list"),
]
