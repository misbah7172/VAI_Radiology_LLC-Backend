import io
import zipfile
import numpy as np

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

    def test_upload_dicom(self):
        """Test uploading a DICOM file and converting it to PNG slices."""
        import pydicom
        from pydicom.dataset import Dataset, FileMetaDataset
        
        file_meta = FileMetaDataset()
        file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
        file_meta.MediaStorageSOPClassUID = pydicom.uid.CTImageStorage
        file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
        
        ds = Dataset()
        ds.file_meta = file_meta
        ds.is_little_endian = True
        ds.is_implicit_VR = False
        ds.SOPClassUID = pydicom.uid.CTImageStorage
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.PatientName = "Test^Patient"
        ds.PatientID = "12345"
        ds.Rows = 10
        ds.Columns = 10
        ds.BitsAllocated = 16
        ds.BitsStored = 12
        ds.HighBit = 11
        ds.PixelRepresentation = 0
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = "MONOCHROME2"
        # 10x10 zero array
        pixel_data = np.zeros((10, 10), dtype=np.uint16)
        ds.PixelData = pixel_data.tobytes()
        
        buffer = io.BytesIO()
        pydicom.filewriter.dcmwrite(buffer, ds, write_like_original=False)
        buffer.seek(0)
        
        dicom_file = SimpleUploadedFile("test.dcm", buffer.read(), content_type="application/dicom")
        response = self.client.post('/api/annotations/images/', {'files': [dicom_file]}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Image.objects.count(), 1)

    def test_upload_zip_archive(self):
        """Test uploading a ZIP archive and extracting its contents."""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            img = PILImage.new('RGB', (10, 10), color='blue')
            img_buf = io.BytesIO()
            img.save(img_buf, format='PNG')
            z.writestr('inner_test.png', img_buf.getvalue())
        buffer.seek(0)
        
        zip_file = SimpleUploadedFile("archive.zip", buffer.read(), content_type="application/zip")
        response = self.client.post('/api/annotations/images/', {'files': [zip_file]}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(Image.objects.count(), 1)

    def test_upload_tiff_converted(self):
        """Test uploading a TIFF image and verifying it is pre-converted to PNG."""
        img = PILImage.new('RGB', (10, 10), color='green')
        buffer = io.BytesIO()
        img.save(buffer, format='TIFF')
        buffer.seek(0)
        
        tiff_file = SimpleUploadedFile("test.tiff", buffer.read(), content_type="image/tiff")
        response = self.client.post('/api/annotations/images/', {'files': [tiff_file]}, format='multipart')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data), 1)
        self.assertTrue(response.data[0]['filename'].endswith('.png'))


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
