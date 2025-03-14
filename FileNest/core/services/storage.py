import os
import hashlib
from typing import BinaryIO, List, Tuple
from minio import Minio
from django.conf import settings
from core.models import File, FileChunk, StorageNode, ChunkLocation

class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the configured bucket exists, create if it doesn't"""
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum of data"""
        return hashlib.sha256(data).hexdigest()

    def _chunk_file(self, file: BinaryIO) -> List[Tuple[int, bytes]]:
        """Split file into chunks"""
        chunks = []
        sequence = 0
        
        while True:
            chunk_data = file.read(settings.MAX_CHUNK_SIZE)
            if not chunk_data:
                break
            chunks.append((sequence, chunk_data))
            sequence += 1
            
        return chunks

    def _select_storage_nodes(self, chunk_size: int, replication_factor: int) -> List[StorageNode]:
        """Select appropriate storage nodes for chunk storage"""
        # Get nodes with enough space, ordered by available space descending
        available_nodes = StorageNode.objects.filter(
            status='ACTIVE',
            capacity__gte=chunk_size
        ).order_by('-available_space')[:replication_factor]
        
        return list(available_nodes)

    def upload_file(self, file: BinaryIO, filename: str, owner) -> File:
        """Upload a file to distributed storage"""
        # Create file record
        file_size = file.seek(0, 2)  # Get file size
        file.seek(0)  # Reset to beginning
        
        file_record = File.objects.create(
            name=filename,
            size=file_size,
            checksum='pending',  # Will be updated after all chunks are processed
            owner=owner
        )

        # Process file in chunks
        file_checksum = hashlib.sha256()
        chunks = self._chunk_file(file)
        
        for sequence, chunk_data in chunks:
            chunk_checksum = self._calculate_checksum(chunk_data)
            file_checksum.update(chunk_data)
            
            # Create chunk record
            chunk = FileChunk.objects.create(
                file=file_record,
                sequence=sequence,
                size=len(chunk_data),
                checksum=chunk_checksum
            )
            
            # Select storage nodes and store chunk
            nodes = self._select_storage_nodes(
                chunk.size,
                settings.REPLICATION_FACTOR
            )
            
            for i, node in enumerate(nodes):
                # Store chunk in MinIO
                object_name = f"{chunk.id}/{node.id}"
                self.client.put_object(
                    self.bucket_name,
                    object_name,
                    chunk_data,
                    len(chunk_data)
                )
                
                # Create chunk location record
                ChunkLocation.objects.create(
                    chunk=chunk,
                    node=node,
                    is_primary=(i == 0)  # First node is primary
                )

        # Update file checksum
        file_record.checksum = file_checksum.hexdigest()
        file_record.save()
        
        return file_record

    def download_file(self, file: File) -> bytes:
        """Download a file from distributed storage"""
        chunks_data = []
        file_checksum = hashlib.sha256()
        
        # Get all chunks in sequence order
        chunks = file.chunks.all()
        
        for chunk in chunks:
            # Get primary location
            location = chunk.chunklocation_set.filter(
                is_primary=True,
                status='AVAILABLE'
            ).first()
            
            if not location:
                # Fallback to any available location
                location = chunk.chunklocation_set.filter(
                    status='AVAILABLE'
                ).first()
            
            if not location:
                raise Exception(f"No available locations for chunk {chunk.id}")
            
            # Get chunk data from MinIO
            object_name = f"{chunk.id}/{location.node.id}"
            try:
                response = self.client.get_object(
                    self.bucket_name,
                    object_name
                )
                chunk_data = response.read()
                response.close()
                response.release_conn()
            except Exception as e:
                raise Exception(f"Failed to retrieve chunk {chunk.id}: {str(e)}")
            
            # Verify checksum
            if self._calculate_checksum(chunk_data) != chunk.checksum:
                raise Exception(f"Chunk {chunk.id} data corruption detected")
            
            chunks_data.append(chunk_data)
            file_checksum.update(chunk_data)
        
        # Verify complete file checksum
        if file_checksum.hexdigest() != file.checksum:
            raise Exception("File data corruption detected")
        
        return b''.join(chunks_data)

    def delete_file(self, file: File):
        """Delete a file from distributed storage"""
        for chunk in file.chunks.all():
            for location in chunk.chunklocation_set.all():
                # Delete from MinIO
                object_name = f"{chunk.id}/{location.node.id}"
                try:
                    self.client.remove_object(self.bucket_name, object_name)
                except:
                    pass  # Best effort deletion
                
                # Delete location record
                location.delete()
            
            # Delete chunk record
            chunk.delete()
        
        # Mark file as deleted
        file.is_deleted = True
        file.save()
