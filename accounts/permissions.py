import json
from functools import wraps

from django.http import JsonResponse

from .models import PermissionRule


def has_access(user, resource_code, action_code):
    if not getattr(user, "is_authenticated", False):
        return False

    if not getattr(user, "is_active", False):
        return False

    role_ids = list(user.role_links.values_list("role_id", flat=True))
    if not role_ids:
        return False

    return PermissionRule.objects.filter(
        role_id__in=role_ids,
        resource__code=resource_code,
        action__code=action_code,
        is_allowed=True,
    ).exists()


def require_auth(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            return JsonResponse({"detail": "Authentication required."}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def require_permission(resource_code, action_code):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.is_active:
                return JsonResponse({"detail": "Authentication required."}, status=401)

            if not has_access(request.user, resource_code, action_code):
                return JsonResponse({"detail": "Access denied."}, status=403)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def parse_json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return None
