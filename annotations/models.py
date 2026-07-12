"""
Models for image upload and polygon annotation.
"""

from django.conf import settings
from django.db import models


class ImageSet(models.Model):
    """A collection of uploaded images grouped as a set."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='image_sets',
    )
    name = models.CharField(max_length=255, default='Unnamed Set')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Stores DICOM tags, NIfTI header info, etc. for medical formats.
    metadata = models.JSONField(null=True, blank=True, default=None)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name



class Image(models.Model):
    """An uploaded image available for annotation."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='images',
    )
    image_set = models.ForeignKey(
        ImageSet,
        on_delete=models.CASCADE,
        related_name='images',
        null=True,
        blank=True,
    )
    file = models.FileField(upload_to='annotations/images/%Y/%m/%d/')
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
    frame_time = models.FloatField(
        null=True, blank=True,
        help_text='Video timestamp in seconds when this annotation was drawn. Null for image annotations.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Annotation on {self.image.filename} ({self.label or "unlabeled"})'
