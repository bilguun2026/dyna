from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from rest.views import UserViewSet, TableViewSet, ColumnViewSet, TableApiViewSet, CellViewSet, WebSocketAPIView
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Router setup for ModelViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'tables', TableViewSet, basename='table')
router.register(r'columns', ColumnViewSet, basename='column')
router.register(r'table-apis', TableApiViewSet, basename='table-api')
router.register(r'cells', CellViewSet, basename='cell')

# Swagger/OpenAPI schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Dynamic Table API",
        default_version='v1',
        description="API documentation for dynamic table structure",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="support@example.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger',
         cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc',
         cache_timeout=0), name='schema-redoc'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/websocket-test/', WebSocketAPIView.as_view(), name='websocket-test'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
