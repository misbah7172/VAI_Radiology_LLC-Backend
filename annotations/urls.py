from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'sets', views.ImageSetViewSet, basename='imageset')
router.register(r'images', views.ImageViewSet, basename='image')
router.register(r'polygons', views.AnnotationViewSet, basename='annotation')

urlpatterns = [
    path('', include(router.urls)),
]
