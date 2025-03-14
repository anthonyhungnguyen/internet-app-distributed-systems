from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileViewSet, StorageNodeViewSet

router = DefaultRouter()
router.register(r'files', FileViewSet)
router.register(r'nodes', StorageNodeViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
