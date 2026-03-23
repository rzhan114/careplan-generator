import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from . import services
from .serializers import ProviderSerializer
from careplan.exception_handler import handle_exception

@csrf_exempt
def provider_list(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            serializer = ProviderSerializer(data)
            serializer.raise_if_invalid()
            validated = serializer.get_validated_data()

            provider = services.create_provider(
                name=validated['name'],
                npi=validated['npi'],
            )

            return JsonResponse({
                "id": provider.id,
                "name": provider.name,
                "npi": provider.npi,
                "created_at": provider.created_at.isoformat(),
            }, status=201)

        except Exception as exc:
            return handle_exception(exc)

    return JsonResponse({"error": "Method not allowed"}, status=405)
