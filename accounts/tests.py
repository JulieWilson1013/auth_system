from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .models import Action, PermissionRule, Resource, Role, UserRole

User = get_user_model()


class AuthAndAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="user@test.local",
            password="User12345!",
            first_name="User",
        )
        self.admin = User.objects.create_user(
            email="admin@test.local",
            password="Admin12345!",
            first_name="Admin",
        )
        admin_role = Role.objects.create(name="Administrator")
        viewer_role = Role.objects.create(name="Viewer")
        projects = Resource.objects.create(code="projects", name="Projects")
        reports = Resource.objects.create(code="reports", name="Reports")
        access_rules = Resource.objects.create(code="access_rules", name="Access rules")
        read = Action.objects.create(code="read", name="Read")
        update = Action.objects.create(code="update", name="Update")

        PermissionRule.objects.create(role=viewer_role, resource=projects, action=read, is_allowed=True)
        PermissionRule.objects.create(role=viewer_role, resource=reports, action=read, is_allowed=False)
        PermissionRule.objects.create(role=admin_role, resource=access_rules, action=read, is_allowed=True)
        PermissionRule.objects.create(role=admin_role, resource=access_rules, action=update, is_allowed=True)

        UserRole.objects.create(user=self.user, role=viewer_role)
        UserRole.objects.create(user=self.admin, role=admin_role)

    def test_login_and_projects_access(self):
        login_response = self.client.post(
            "/api/auth/login",
            data={"email": "user@test.local", "password": "User12345!"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 200)

        projects_response = self.client.get("/api/business/projects")
        self.assertEqual(projects_response.status_code, 200)

        reports_response = self.client.get("/api/business/reports")
        self.assertEqual(reports_response.status_code, 403)

    def test_soft_delete_blocks_future_login(self):
        self.client.post(
            "/api/auth/login",
            data={"email": "user@test.local", "password": "User12345!"},
            content_type="application/json",
        )
        delete_response = self.client.delete("/api/users/me/delete")
        self.assertEqual(delete_response.status_code, 200)

        login_response = self.client.post(
            "/api/auth/login",
            data={"email": "user@test.local", "password": "User12345!"},
            content_type="application/json",
        )
        self.assertEqual(login_response.status_code, 401)

    def test_non_admin_cannot_read_rules(self):
        self.client.post(
            "/api/auth/login",
            data={"email": "user@test.local", "password": "User12345!"},
            content_type="application/json",
        )
        response = self.client.get("/api/admin/permissions")
        self.assertEqual(response.status_code, 403)
