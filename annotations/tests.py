import io

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image as PILImage

from accounts.models import User
from .models import Image, Annotation


def create_test_image(name='test.png', size=(100, 100)):
    """Create a minimal valid PNG image for testing."""
    img = PILImage.new('RGB', size, color='red')
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(name, buffer.read(), content_type='image/png')


class ImageAPITests(TestCase):
    """Tests for image upload and management endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_upload_single_image(self):
        img = create_test_image()
        response = self.client.post('/api/annotations/images/', {'files': [img]}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Image.objects.count(), 1)

    def test_list_images(self):
        Image.objects.create(
            user=self.user,
            file=create_test_image(),
            filename='test.png',
        )
        response = self.client.get('/api/annotations/images/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_delete_image(self):
        image = Image.objects.create(
            user=self.user,
            file=create_test_image(),
            filename='test.png',
        )
        response = self.client.delete(f'/api/annotations/images/{image.id}/')
        self.assertEqual(response.status_code, 204)


class AnnotationAPITests(TestCase):
    """Tests for polygon annotation endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com', password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.image = Image.objects.create(
            user=self.user,
            file=create_test_image(),
            filename='test.png',
        )

    def test_create_annotation(self):
        response = self.client.post('/api/annotations/polygons/', {
            'image': self.image.id,
            'label': 'Tumor',
            'color': '#FF0000',
            'polygon_data': [
                {'x': 10, 'y': 10},
                {'x': 50, 'y': 10},
                {'x': 50, 'y': 50},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Annotation.objects.count(), 1)

    def test_annotation_requires_3_points(self):
        response = self.client.post('/api/annotations/polygons/', {
            'image': self.image.id,
            'polygon_data': [
                {'x': 10, 'y': 10},
                {'x': 50, 'y': 10},
            ],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_delete_annotation(self):
        annotation = Annotation.objects.create(
            image=self.image,
            label='Test',
            polygon_data=[{'x': 0, 'y': 0}, {'x': 1, 'y': 0}, {'x': 0, 'y': 1}],
        )
        response = self.client.delete(f'/api/annotations/polygons/{annotation.id}/')
        self.assertEqual(response.status_code, 204)
