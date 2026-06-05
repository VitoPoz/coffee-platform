from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import os

@csrf_exempt
def upload_pdf(request):
    if request.method == 'POST':
        file = request.FILES.get('pdf')
        if file and file.name.endswith('.pdf'):
            # Сохраняем файл в папку media/presentations
            os.makedirs('media/presentations', exist_ok=True)
            file_path = f'media/presentations/{file.name}'
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return JsonResponse({'url': f'/{file_path}'})
    return JsonResponse({'error': 'Нет файла'}, status=400)