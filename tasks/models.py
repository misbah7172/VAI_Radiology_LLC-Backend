"""
Task model for the Kanban board.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone


class Task(models.Model):
    """A task on the Kanban board, scoped to a user and date."""

    class Status(models.TextChoices):
        TODO = 'todo', 'To Do'
        IN_PROGRESS = 'in_progress', 'In Progress'
        DONE = 'done', 'Done'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    start_date = models.DateTimeField(default=timezone.now)
    due_date = models.DateTimeField()
    tags = models.JSONField(default=list, blank=True)
    position = models.IntegerField(default=0, help_text='Order within the column')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['position', '-created_at']

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'
