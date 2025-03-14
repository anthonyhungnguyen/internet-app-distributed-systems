from django.contrib import admin
from .models import StorageNode, File, FileChunk, ChunkLocation

@admin.register(StorageNode)
class StorageNodeAdmin(admin.ModelAdmin):
    list_display = ('address', 'status', 'capacity', 'used_space', 'available_space', 'last_heartbeat')
    list_filter = ('status',)
    search_fields = ('address',)
    readonly_fields = ('last_heartbeat', 'created_at')

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'size', 'created_at', 'is_deleted')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('name', 'owner__username')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(FileChunk)
class FileChunkAdmin(admin.ModelAdmin):
    list_display = ('file', 'sequence', 'size', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('file__name',)
    readonly_fields = ('created_at',)

@admin.register(ChunkLocation)
class ChunkLocationAdmin(admin.ModelAdmin):
    list_display = ('chunk', 'node', 'is_primary', 'status', 'last_verified')
    list_filter = ('is_primary', 'status', 'created_at')
    search_fields = ('chunk__file__name', 'node__address')
    readonly_fields = ('created_at', 'last_verified')
