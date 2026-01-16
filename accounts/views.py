from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import Action, PermissionRule, Resource, Role, UserRole
from .permissions import parse_json_body, require_auth, require_permission

User = get_user_model()


@require_GET
def api_root(request):
    """Friendly index for /api/ so clients see a deliberate overview, not a missing route."""
    return JsonResponse(
        {
            "status": "ok",
            "message": "API is available. Use POST/GET/etc. on the paths below (JSON bodies where noted).",
            "authentication": {
                "register": "POST /api/auth/register",
                "login": "POST /api/auth/login",
                "logout": "POST /api/auth/logout",
            },
            "profile": {
                "me_get": "GET /api/users/me",
                "me_patch": "PATCH /api/users/me",
                "soft_delete": "DELETE /api/users/me/delete",
            },
            "business_demo": {
                "projects": "GET /api/business/projects",
                "reports": "GET /api/business/reports",
            },
            "admin_rules": {
                "list": "GET /api/admin/permissions",
                "create_or_update": "POST /api/admin/permissions/create",
                "delete": "DELETE /api/admin/permissions/<rule_id>",
                "assign_role": "POST /api/admin/users/<user_id>/roles",
            },
            "hint": "After login, send cookies on follow-up requests (e.g. Postman: enable cookies).",
        }
    )


def _user_payload(user):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name,
        "is_active": user.is_active,
    }


@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    required_fields = ["email", "password", "password_confirm", "first_name"]
    missing = [field for field in required_fields if not body.get(field)]
    if missing:
        return JsonResponse({"detail": f"Missing fields: {', '.join(missing)}."}, status=400)

    if body["password"] != body["password_confirm"]:
        return JsonResponse({"detail": "Password confirmation does not match."}, status=400)

    try:
        user = User.objects.create_user(
            email=body["email"],
            password=body["password"],
            first_name=body["first_name"],
            last_name=body.get("last_name", ""),
            middle_name=body.get("middle_name", ""),
        )
    except IntegrityError:
        return JsonResponse({"detail": "A user with this email already exists."}, status=400)

    return JsonResponse({"user": _user_payload(user)}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login_view(request):
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        return JsonResponse({"detail": "Email and password are required."}, status=400)

    user = authenticate(request, email=email, password=password)
    if user is None:
        return JsonResponse({"detail": "Invalid credentials."}, status=401)

    if not user.is_active:
        return JsonResponse({"detail": "Account is deactivated."}, status=401)

    login(request, user)
    return JsonResponse({"detail": "Login successful.", "user": _user_payload(user)})


@csrf_exempt
@require_http_methods(["POST"])
@require_auth
def logout_view(request):
    logout(request)
    return JsonResponse({"detail": "Logout successful."})


@csrf_exempt
@require_http_methods(["GET", "PATCH"])
@require_auth
def me(request):
    if request.method == "GET":
        return JsonResponse({"user": _user_payload(request.user)})

    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    updatable_fields = ["first_name", "last_name", "middle_name"]
    for field in updatable_fields:
        if field in body:
            setattr(request.user, field, body[field])

    request.user.save(update_fields=updatable_fields + ["updated_at"])
    return JsonResponse({"detail": "Profile updated.", "user": _user_payload(request.user)})


@csrf_exempt
@require_http_methods(["DELETE"])
@require_auth
def delete_me(request):
    user = request.user
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    logout(request)
    return JsonResponse({"detail": "Account deleted (soft delete)."})


@require_GET
@require_permission("access_rules", "read")
def admin_permissions_list(request):
    rules = PermissionRule.objects.select_related("role", "resource", "action").all()
    return JsonResponse(
        {
            "permissions": [
                {
                    "id": rule.id,
                    "role": rule.role.name,
                    "resource": rule.resource.code,
                    "action": rule.action.code,
                    "is_allowed": rule.is_allowed,
                }
                for rule in rules
            ]
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_permission("access_rules", "update")
def admin_permissions_create(request):
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    role_name = body.get("role")
    resource_code = body.get("resource")
    action_code = body.get("action")
    is_allowed = body.get("is_allowed", True)

    if not role_name or not resource_code or not action_code:
        return JsonResponse({"detail": "role, resource and action are required."}, status=400)

    try:
        role = Role.objects.get(name=role_name)
        resource = Resource.objects.get(code=resource_code)
        action = Action.objects.get(code=action_code)
    except (Role.DoesNotExist, Resource.DoesNotExist, Action.DoesNotExist):
        return JsonResponse({"detail": "Role/resource/action was not found."}, status=400)

    rule, created = PermissionRule.objects.update_or_create(
        role=role,
        resource=resource,
        action=action,
        defaults={"is_allowed": bool(is_allowed)},
    )

    status_code = 201 if created else 200
    return JsonResponse({"detail": "Permission rule saved.", "id": rule.id}, status=status_code)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_permission("access_rules", "update")
def admin_permissions_delete(request, rule_id):
    deleted, _ = PermissionRule.objects.filter(id=rule_id).delete()
    if deleted == 0:
        return JsonResponse({"detail": "Permission rule not found."}, status=404)
    return JsonResponse({"detail": "Permission rule deleted."})


@csrf_exempt
@require_http_methods(["POST"])
@require_permission("access_rules", "update")
def admin_assign_role(request, user_id):
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    role_name = body.get("role")
    if not role_name:
        return JsonResponse({"detail": "role is required."}, status=400)

    try:
        target_user = User.objects.get(id=user_id)
        role = Role.objects.get(name=role_name)
    except (User.DoesNotExist, Role.DoesNotExist):
        return JsonResponse({"detail": "User or role not found."}, status=404)

    UserRole.objects.get_or_create(user=target_user, role=role)
    return JsonResponse({"detail": "Role assigned."})


@require_GET
@require_permission("projects", "read")
def projects_list(request):
    return JsonResponse(
        {
            "projects": [
                {"id": 1, "name": "Payroll migration"},
                {"id": 2, "name": "Mobile onboarding"},
            ]
        }
    )


@require_GET
@require_permission("reports", "read")
def reports_list(request):
    return JsonResponse(
        {
            "reports": [
                {"id": 1, "name": "Monthly sales report"},
                {"id": 2, "name": "Fraud risk report"},
            ]
        }
    )
