"""
Lightweight entry points so opening the site root in a browser is clearly intentional,
not a broken page or empty 404.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_GET


@require_GET
def site_root(request):
    return JsonResponse(
        {
            "status": "ok",
            "service": "Authentication & authorization API (Django)",
            "message": "The server is running. This project is a JSON API, not a website with HTML pages.",
            "start_here": "/api/",
            "documentation": "See README.md in the repository for setup and endpoint details.",
        }
    )
