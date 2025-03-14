from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.uploadedfile import UploadedFile
from .models import File, StorageNode
from .serializers import FileSerializer, StorageNodeSerializer
from .services.storage import StorageService

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.filter(is_deleted=False)
    serializer_class = FileSerializer
    permission_classes = [IsAuthenticated]
    storage_service = StorageService()

    def get_queryset(self):
        return self.queryset.filter(owner=self.request.user)

    def create(self, request, *args, **kwargs):
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        uploaded_file: UploadedFile = request.FILES['file']
        
        try:
            file_record = self.storage_service.upload_file(
                file=uploaded_file,
                filename=uploaded_file.name,
                owner=request.user
            )
            serializer = self.get_serializer(file_record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        file = self.get_object()
        try:
            self.storage_service.delete_file(file)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        file = self.get_object()
        try:
            file_data = self.storage_service.download_file(file)
            response = Response(file_data, content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{file.name}"'
            return response
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class StorageNodeViewSet(viewsets.ModelViewSet):
    queryset = StorageNode.objects.all()
    serializer_class = StorageNodeSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def toggle_maintenance(self, request, pk=None):
        node = self.get_object()
        if node.status == 'ACTIVE':
            node.status = 'MAINTENANCE'
        elif node.status == 'MAINTENANCE':
            node.status = 'ACTIVE'
        node.save()
        return Response(self.get_serializer(node).data)
