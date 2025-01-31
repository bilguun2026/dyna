from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination
import websockets
from asgiref.sync import async_to_sync
from rest_framework.decorators import api_view
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
import websockets
import asyncio

from .models import User, Table, Column, TableApi, Cell
from .serializers import UserSerializer, TableSerializer, ColumnSerializer, TableApiSerializer, CellSerializer

# Pagination class for handling large datasets


class LargeDataPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [IsAuthenticated, IsAdminUser]
    # authentication_classes = [JWTAuthentication]
    pagination_class = LargeDataPagination


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    # permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']

    # @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    # def duplicate(self, request, pk=None):
    #     table = self.get_object()
    #     # Logic to duplicate a table could involve deep copying the table record and its related data
    #     return Response({'status': 'Table duplicated successfully'})


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    # permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['name', 'data_type']
    ordering_fields = ['name', 'data_type']


class TableApiViewSet(viewsets.ModelViewSet):
    queryset = TableApi.objects.select_related(
        'table').prefetch_related('api_cells')
    serializer_class = TableApiSerializer
    permission_classes = [IsAuthenticated]


class CellViewSet(viewsets.ModelViewSet):
    queryset = Cell.objects.select_related(
        'column', 'table_api').prefetch_related('table_api__user')
    serializer_class = CellSerializer
    # permission_classes = [IsAuthenticated]


class WebSocketAPIView(APIView):
    async def get(self, request, *args, **kwargs):
        url = "ws://192.168.88.10:8080"
        try:
            async with websockets.connect(url) as websocket:
                return print("greeting")
        except Exception as e:
            return Response({"error": str(e)}, status=500)
