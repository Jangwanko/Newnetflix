# mynetflix/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from movies import consumers  # consumer 모듈을 생성해야 합니다.

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mynetflix.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter([
            path('ws/upload_progress/', consumers.UploadProgressConsumer.as_asgi()),
        ])
    ),
})
