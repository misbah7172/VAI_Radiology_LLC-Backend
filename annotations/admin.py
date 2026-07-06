from django.contrib import admin
from .models import Image, Annotation


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('filename', 'user', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('filename',)


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ('image', 'label', 'color', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('label',)
