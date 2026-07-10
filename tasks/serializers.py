from rest_framework import serializers
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """Full Task serializer for CRUD operations."""

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'start_date', 'due_date', 'tags', 'position', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_tags(self, value):
        """Ensure tags is a list of strings."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Tags must be a list.')
        if not all(isinstance(tag, str) for tag in value):
            raise serializers.ValidationError('Each tag must be a string.')
        return value


class TaskStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status/position updates (drag-and-drop)."""

    id = serializers.IntegerField()
    status = serializers.ChoiceField(choices=Task.Status.choices)
    position = serializers.IntegerField()
