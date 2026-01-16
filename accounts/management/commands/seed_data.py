from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Action, PermissionRule, Resource, Role, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = "Seed test data for auth and access-control demo."

    @transaction.atomic
    def handle(self, *args, **options):
        admin_role, _ = Role.objects.get_or_create(name="Administrator", defaults={"description": "System administrator"})
        manager_role, _ = Role.objects.get_or_create(name="Manager")
        viewer_role, _ = Role.objects.get_or_create(name="Viewer")

        resources = [
            ("access_rules", "Access control rules"),
            ("projects", "Projects mock resource"),
            ("reports", "Reports mock resource"),
        ]
        for code, name in resources:
            Resource.objects.get_or_create(code=code, defaults={"name": name})

        actions = [("read", "Read"), ("update", "Update")]
        for code, name in actions:
            Action.objects.get_or_create(code=code, defaults={"name": name})

        def rule(role_name, resource_code, action_code, is_allowed=True):
            role = Role.objects.get(name=role_name)
            resource = Resource.objects.get(code=resource_code)
            action = Action.objects.get(code=action_code)
            PermissionRule.objects.update_or_create(
                role=role,
                resource=resource,
                action=action,
                defaults={"is_allowed": is_allowed},
            )

        rule("Administrator", "access_rules", "read", True)
        rule("Administrator", "access_rules", "update", True)
        rule("Administrator", "projects", "read", True)
        rule("Administrator", "reports", "read", True)
        rule("Manager", "projects", "read", True)
        rule("Manager", "reports", "read", True)
        rule("Viewer", "projects", "read", True)
        rule("Viewer", "reports", "read", False)

        # Always set known passwords for demo accounts so login works even if rows
        # were created manually, migrated oddly, or had empty/unusable passwords.
        admin_user, _ = User.objects.get_or_create(
            email="admin@test.local",
            defaults={
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
            },
        )
        admin_user.first_name = admin_user.first_name or "Admin"
        admin_user.last_name = admin_user.last_name or "User"
        admin_user.is_staff = True
        admin_user.is_active = True
        admin_user.set_password("Admin12345!")
        admin_user.save()

        manager_user, _ = User.objects.get_or_create(
            email="manager@test.local",
            defaults={"first_name": "Manager"},
        )
        manager_user.is_active = True
        manager_user.set_password("Manager12345!")
        manager_user.save()

        viewer_user, _ = User.objects.get_or_create(
            email="viewer@test.local",
            defaults={"first_name": "Viewer"},
        )
        viewer_user.is_active = True
        viewer_user.set_password("Viewer12345!")
        viewer_user.save()

        UserRole.objects.get_or_create(user=admin_user, role=admin_role)
        UserRole.objects.get_or_create(user=manager_user, role=manager_role)
        UserRole.objects.get_or_create(user=viewer_user, role=viewer_role)

        self.stdout.write(self.style.SUCCESS("Seed data has been created/updated."))
