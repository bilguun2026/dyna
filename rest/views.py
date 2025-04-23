from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import websockets
import pandas as pd
from rest_framework import status
from django.db import transaction
import logging


from .models import (
    File, Image, TableCategory, User, Table, Column, TableApi, Cell,
    Company, Project, Job, Operation, FormulaStep
)
from .serializers import (
    FileUploadSerializer, ImageUploadSerializer, TableCategorySerializer, UserSerializer, TableSerializer, ColumnSerializer, TableApiSerializer, CellSerializer,
    CompanySerializer, ProjectSerializer, JobSerializer, OperationSerializer, FormulaStepSerializer
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
    queryset = Column.objects.prefetch_related(
        'options', 'formula_steps').all()
    serializer_class = ColumnSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['name', 'data_type']
    ordering_fields = ['name', 'data_type']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Operation ViewSet (New)
# ------------------------------------------------------------------------------


class OperationViewSet(viewsets.ModelViewSet):
    queryset = Operation.objects.all()
    serializer_class = OperationSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# FormulaStep ViewSet (New)
# ------------------------------------------------------------------------------


class FormulaStepViewSet(viewsets.ModelViewSet):
    queryset = FormulaStep.objects.select_related('column', 'operation').all()
    serializer_class = FormulaStepSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['column', 'operation', 'order']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# TableApi ViewSet
# ------------------------------------------------------------------------------


class TableApiViewSet(viewsets.ModelViewSet):
    queryset = TableApi.objects.select_related(
        'table', 'user').prefetch_related('api_cells').all()
    serializer_class = TableApiSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ------------------------------------------------------------------------------
# Cell ViewSet
# ------------------------------------------------------------------------------


class CellViewSet(viewsets.ModelViewSet):
    queryset = Cell.objects.select_related('column', 'table_api').prefetch_related(
        'table_api__user', 'files', 'images').all()
    serializer_class = CellSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Company ViewSet
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
# Project ViewSet
# ------------------------------------------------------------------------------


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related(
        'company').prefetch_related('jobs').all()
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    permission_classes = [IsAuthenticated]
    authentication_classes = [JWTAuthentication]

# ------------------------------------------------------------------------------
# Job ViewSet
# ------------------------------------------------------------------------------


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related('project').prefetch_related(
        'advisorCompanies', 'contractorCompanies', 'job_table_collection').all()
    serializer_class = JobSerializer
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'created_at']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    permission_classes = [IsAuthenticated]
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

# ------------------------------------------------------------------------------
# TableCategory API View
# ------------------------------------------------------------------------------


class TableCategoryViewSet(viewsets.ModelViewSet):
    queryset = TableCategory.objects.all().order_by('order_number')
    serializer_class = TableCategorySerializer

# ------------------------------------------------------------------------------
# FileUpload ViewSet
# ------------------------------------------------------------------------------


class FileUploadViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileUploadSerializer

# ------------------------------------------------------------------------------
# ImageUpload ViewSet
# ------------------------------------------------------------------------------


class ImageUploadViewSet(viewsets.ModelViewSet):
    queryset = Image.objects.all()
    serializer_class = ImageUploadSerializer


@require_GET
def get_columns_for_table(request):
    table_id = request.GET.get('table_id')
    if table_id:
        columns = Column.objects.filter(table_id=table_id).values('name')
        return JsonResponse({'columns': list(columns)})
    return JsonResponse({'columns': []})


# ------------------------------------------------------------------------------
# ImageUpload ViewSet
# ------------------------------------------------------------------------------
logger = logging.getLogger(__name__)


class ExcelUploadView(APIView):
    def post(self, request):
        logger.debug(f"Raw request data: {request.data}")
        serializer = FileUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        excel_file = serializer.validated_data['file']
        table_id = serializer.validated_data['table_id']
        column_ids = serializer.validated_data['column_ids']
        job_id = serializer.validated_data.get('job_id')
        strict_numeric = serializer.validated_data['strict_numeric']

        try:
            with transaction.atomic():
                df = pd.read_excel(excel_file, dtype_backend='numpy_nullable')
                excel_columns = df.columns.tolist()
                table = Table.objects.get(id=table_id)
                columns = Column.objects.filter(id__in=column_ids, table=table)
                column_map = {col.name: col for col in columns}
                unmatched_columns = [
                    col for col in excel_columns if col not in column_map]
                if unmatched_columns:
                    return Response(
                        {'error': f"Excel columns {unmatched_columns} do not match any provided column names"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                job = None
                if job_id:
                    try:
                        job = Job.objects.get(id=job_id)
                    except Job.DoesNotExist:
                        return Response(
                            {'error': f'Job with id {job_id} not found'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                table_api = TableApi.objects.create(
                    table=table,
                    job=job,
                    user=request.user if request.user.is_authenticated else None
                )
                created_cells = []
                for index, row in df.iterrows():
                    for col_name in excel_columns:
                        value = row[col_name]
                        column = column_map[col_name]
                        if pd.isna(value):
                            value = ''
                        else:
                            if column.data_type == 'number':
                                try:
                                    value = float(value)
                                    value = str(value)
                                except (ValueError, TypeError):
                                    if strict_numeric:
                                        return Response(
                                            {'error': f'Invalid numeric value "{value}" in column "{col_name}" at row {index + 2}'},
                                            status=status.HTTP_400_BAD_REQUEST
                                        )
                                    value = ''
                            else:
                                value = str(value)
                        cell = Cell.objects.create(
                            table_api=table_api,
                            column=column,
                            value=value,
                            is_required=False
                        )
                        created_cells.append(cell)
                response_serializer = CellSerializer(created_cells, many=True)
                return Response(
                    {
                        'message': 'Data successfully uploaded and saved',
                        'table_id': str(table.id),
                        'table_api_id': str(table_api.id),
                        'cells': response_serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
        except Exception as e:
            return Response(
                {'error': f'Error processing file: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
