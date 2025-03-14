from rest_framework import serializers
from .models import File, StorageNode

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ['id', 'name', 'size', 'checksum', 'created_at', 'updated_at']
        read_only_fields = ['id', 'size', 'checksum', 'created_at', 'updated_at']

class StorageNodeSerializer(serializers.ModelSerializer):
    available_space = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StorageNode
        fields = ['id', 'address', 'status', 'capacity', 'used_space', 'available_space', 'last_heartbeat']
        read_only_fields = ['id', 'last_heartbeat']
