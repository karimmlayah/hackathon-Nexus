from django.http import JsonResponse

from .qdrant import qdrant_ping


def qdrant_health(request):
    try:
        data = qdrant_ping()
        return JsonResponse(data, status=200)
    except Exception as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)

