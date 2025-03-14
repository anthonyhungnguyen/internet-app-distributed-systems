from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
import uuid

class StorageNode(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('MAINTENANCE', 'Maintenance'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    address = models.CharField(max_length=255)
    capacity = models.BigIntegerField(validators=[MinValueValidator(0)])
    used_space = models.BigIntegerField(default=0, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    last_heartbeat = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'storage_nodes'

    def __str__(self):
        return f"{self.address} ({self.status})"

    @property
    def available_space(self):
        return max(0, self.capacity - self.used_space)

class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    size = models.BigIntegerField(validators=[MinValueValidator(0)])
    checksum = models.CharField(max_length=64)  # SHA-256 hash
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = 'files'

    def __str__(self):
        return self.name

class FileChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.ForeignKey(File, related_name='chunks', on_delete=models.CASCADE)
    sequence = models.IntegerField(validators=[MinValueValidator(0)])
    size = models.BigIntegerField(validators=[MinValueValidator(0)])
    checksum = models.CharField(max_length=64)  # SHA-256 hash
    storage_nodes = models.ManyToManyField(StorageNode, through='ChunkLocation')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'file_chunks'
        unique_together = ['file', 'sequence']
        ordering = ['sequence']

    def __str__(self):
        return f"{self.file.name} - Chunk {self.sequence}"

class ChunkLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chunk = models.ForeignKey(FileChunk, on_delete=models.CASCADE)
    node = models.ForeignKey(StorageNode, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_verified = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='AVAILABLE')

    class Meta:
        db_table = 'chunk_locations'
        unique_together = ['chunk', 'node']

    def __str__(self):
        return f"{self.chunk} on {self.node}"
