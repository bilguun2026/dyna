from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
import asyncio
import websockets

from .models import (
    User, Table, Column, TableApi, Cell,
    Company, Project, Job
)
from .serializers import (
    UserSerializer, TableSerializer, ColumnSerializer, TableApiSerializer, CellSerializer,
    CompanySerializer, ProjectSerializer, JobSerializer
)

# ------------------------------------------------------------------------------
# Pagination for handling large datasets
# ------------------------------------------------------------------------------


class LargeDataPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000

# ------------------------------------------------------------------------------
# User ViewSet
# ------------------------------------------------------------------------------


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = LargeDataPagination
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Table ViewSet
# ------------------------------------------------------------------------------


class TableViewSet(viewsets.ModelViewSet):
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Column ViewSet
# ------------------------------------------------------------------------------


class ColumnViewSet(viewsets.ModelViewSet):
    queryset = Column.objects.all()
    serializer_class = ColumnSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['name', 'data_type']
    ordering_fields = ['name', 'data_type']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# TableApi ViewSet
# ------------------------------------------------------------------------------


class TableApiViewSet(viewsets.ModelViewSet):
    queryset = TableApi.objects.select_related(
        'table').prefetch_related('api_cells')
    serializer_class = TableApiSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]


# ------------------------------------------------------------------------------
# Cell ViewSet
# ------------------------------------------------------------------------------


class CellViewSet(viewsets.ModelViewSet):
    queryset = Cell.objects.select_related(
        'column', 'table_api').prefetch_related('table_api__user')
    serializer_class = CellSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Company ViewSet (new)
# ------------------------------------------------------------------------------


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name']
    search_fields = ['name']
    ordering_fields = ['name']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Project ViewSet (new)
# ------------------------------------------------------------------------------


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related('company').all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Job ViewSet (new)
# ------------------------------------------------------------------------------


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related('project')\
        .prefetch_related('advisorCompanies', 'contractorCompanies').all()
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    # permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# WebSocket API View
# ------------------------------------------------------------------------------


class WebSocketAPIView(APIView):
    """
    An async API view that connects to a WebSocket server.
    Make sure your Django project supports async views (Django 3.1+).
    """

    async def get(self, request, *args, **kwargs):
        url = "ws://192.168.88.10:8080"
        try:
            async with websockets.connect(url) as websocket:
                # For example, wait for a greeting message from the server.
                greeting = await websocket.recv()
                return Response({"message": greeting})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
