from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Task
from .serializers import TaskSerializer, TaskStatusUpdateSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """
    CRUD ViewSet for Tasks, scoped to the authenticated user.
    Supports filtering by date via ?date=YYYY-MM-DD query parameter.
    """

    serializer_class = TaskSerializer

    def get_queryset(self):
        qs = Task.objects.filter(user=self.request.user)

        # Filter by date if provided
        date = self.request.query_params.get('date')
        if date:
            qs = qs.filter(due_date=date)

        # Filter by status if provided
        task_status = self.request.query_params.get('status')
        if task_status:
            qs = qs.filter(status=task_status)

        # Filter by tag (case-insensitive substring match across all dates)
        tag = self.request.query_params.get('tag', '').strip()
        if tag:
            # JSON contains icontains — works for both SQLite & Postgres
            qs = qs.filter(tags__icontains=tag)

        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Bulk update task status and position (for drag-and-drop).

        POST /api/tasks/reorder/
        Body: { "tasks": [{ "id": 1, "status": "in_progress", "position": 0 }, ...] }
        """
        serializer = TaskStatusUpdateSerializer(data=request.data.get('tasks', []), many=True)
        serializer.is_valid(raise_exception=True)

        task_ids = [item['id'] for item in serializer.validated_data]
        tasks = Task.objects.filter(id__in=task_ids, user=request.user)
        task_map = {task.id: task for task in tasks}

        updated = []
        for item in serializer.validated_data:
            task = task_map.get(item['id'])
            if task:
                task.status = item['status']
                task.position = item['position']
                updated.append(task)

        Task.objects.bulk_update(updated, ['status', 'position'])

        return Response({'updated': len(updated)}, status=status.HTTP_200_OK)
