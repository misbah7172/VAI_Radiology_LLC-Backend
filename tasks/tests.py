import json
from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from .models import Task


class TaskModelTests(TestCase):
    """Tests for the Task model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )

    def test_create_task(self):
        task = Task.objects.create(
            user=self.user,
            title='Test Task',
            status='todo',
            priority='medium',
            due_date=date.today(),
            tags=['bug', 'urgent'],
        )
        self.assertEqual(task.title, 'Test Task')
        self.assertEqual(task.status, 'todo')
        self.assertEqual(task.tags, ['bug', 'urgent'])

    def test_task_str(self):
        task = Task.objects.create(
            user=self.user,
            title='My Task',
            due_date=date.today(),
        )
        self.assertIn('My Task', str(task))


class TaskAPITests(TestCase):
    """Tests for Task API endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.today = date.today().isoformat()

    def test_create_task(self):
        response = self.client.post('/api/tasks/', {
            'title': 'New Task',
            'status': 'todo',
            'priority': 'high',
            'due_date': self.today,
            'tags': ['frontend'],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], 'New Task')

    def test_list_tasks_filtered_by_date(self):
        Task.objects.create(
            user=self.user, title='Today', due_date=self.today
        )
        Task.objects.create(
            user=self.user, title='Other', due_date='2025-01-01'
        )
        response = self.client.get(f'/api/tasks/?date={self.today}')
        self.assertEqual(response.status_code, 200)
        titles = [t['title'] for t in response.data['results']]
        self.assertIn('Today', titles)
        self.assertNotIn('Other', titles)

    def test_update_task(self):
        task = Task.objects.create(
            user=self.user, title='Old Title', due_date=self.today
        )
        response = self.client.patch(f'/api/tasks/{task.id}/', {
            'title': 'New Title',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'New Title')

    def test_delete_task(self):
        task = Task.objects.create(
            user=self.user, title='Delete Me', due_date=self.today
        )
        response = self.client.delete(f'/api/tasks/{task.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Task.objects.filter(id=task.id).exists())

    def test_reorder_tasks(self):
        t1 = Task.objects.create(
            user=self.user, title='T1', due_date=self.today, status='todo'
        )
        t2 = Task.objects.create(
            user=self.user, title='T2', due_date=self.today, status='todo'
        )
        response = self.client.post('/api/tasks/reorder/', {
            'tasks': [
                {'id': t1.id, 'status': 'in_progress', 'position': 1},
                {'id': t2.id, 'status': 'done', 'position': 0},
            ]
        }, format='json')
        self.assertEqual(response.status_code, 200)
        t1.refresh_from_db()
        t2.refresh_from_db()
        self.assertEqual(t1.status, 'in_progress')
        self.assertEqual(t2.status, 'done')

    def test_tasks_scoped_to_user(self):
        other_user = User.objects.create_user(
            email='other@example.com', password='pass123'
        )
        Task.objects.create(
            user=other_user, title='Other User Task', due_date=self.today
        )
        response = self.client.get('/api/tasks/')
        self.assertEqual(response.status_code, 200)
        titles = [t['title'] for t in response.data['results']]
        self.assertNotIn('Other User Task', titles)
