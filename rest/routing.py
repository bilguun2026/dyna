# your_project_name/routing.py

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from .consumers import MyConsumer

application = ProtocolTypeRouter({
    'websocket': URLRouter([
        path('ws/some_path/', MyConsumer.as_asgi()),
    ])
})
