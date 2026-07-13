from rest_framework import serializers
from .models import Image, Annotation, ImageSet


class AnnotationSerializer(serializers.ModelSerializer):
    """Serializer for polygon annotations."""

    class Meta:
        model = Annotation
        fields = ['id', 'image', 'label', 'color', 'polygon_data', 'frame_time', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_polygon_data(self, value):
        """Ensure polygon_data is a list of {x, y} coordinate objects."""
        if not isinstance(value, list):
            raise serializers.ValidationError('polygon_data must be a list of points.')
        if len(value) < 3:
            raise serializers.ValidationError('A polygon needs at least 3 points.')
        for point in value:
            if not isinstance(point, dict) or 'x' not in point or 'y' not in point:
                raise serializers.ValidationError(
                    'Each point must be an object with "x" and "y" keys.'
                )
        return value


class ImageSerializer(serializers.ModelSerializer):
    """Serializer for uploaded images, includes nested annotations."""

    annotations = AnnotationSerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Image
        fields = ['id', 'filename', 'file', 'file_url', 'uploaded_at', 'image_set', 'annotations']
        read_only_fields = ['id', 'filename', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        if request:
            return request.build_absolute_uri(obj.file.url)
        # Fallback: return the relative URL — the frontend will prepend the API base URL
        return obj.file.url


class ImageSetSerializer(serializers.ModelSerializer):
    """Serializer for collections of uploaded images."""

    images = ImageSerializer(many=True, read_only=True)

    class Meta:
        model = ImageSet
        fields = ['id', 'name', 'created_at', 'updated_at', 'metadata', 'images']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ImageUploadSerializer(serializers.Serializer):
    """Serializer for handling multi-file image uploads."""

    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
    )
