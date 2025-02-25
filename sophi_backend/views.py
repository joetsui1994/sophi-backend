import subprocess
from django.db import connections
from django.http import JsonResponse
from django.conf import settings


def get_git_version():
    """Retrieve the current Git commit hash as the app version."""
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"


def health_check(request):
    """Returns system health status and version info."""
    # Check database connectivity
    try:
        connections["default"].cursor()
        db_status = "ok"
    except Exception:
        db_status = "error"

    response_data = {
        "status": db_status,
        "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else None,
        "git_version": get_git_version(),  # Retrieve from Git
        "debug": settings.DEBUG,  # Show if debug mode is enabled
    }

    return JsonResponse(response_data)