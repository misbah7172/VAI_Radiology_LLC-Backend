"""
Models for image upload and polygon annotation.
"""

from django.conf import settings
from django.db import models


class Image(models.Model):
    """An uploaded image available for annotation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='images',
    )
    file = models.ImageField(upload_to='annotations/images/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.filename


class Annotation(models.Model):
    """A polygon annotation drawn on an image."""

    image = models.ForeignKey(
        Image,
        on_delete=models.CASCADE,
        related_name='annotations',
    )
    label = models.CharField(max_length=255, blank=True, default='')
    color = models.CharField(max_length=7, default='#FF6B6B')
    polygon_data = models.JSONField(
        help_text='Array of {x, y} coordinates forming the polygon vertices'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Annotation on {self.image.filename} ({self.label or "unlabeled"})'
