import io
import logging
import zipfile
from PIL import Image as PILImage
from django.core.files.base import ContentFile
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Image, Annotation, ImageSet
from .serializers import ImageSerializer, AnnotationSerializer, ImageSetSerializer
from .medical_utils import is_medical, convert_medical_file, needs_browser_conversion

logger = logging.getLogger(__name__)


def optimize_uploaded_image(uploaded_file):
    """
    Optimizes and compresses uploaded images (JPEG/PNG) to save storage/bandwidth.
    Falls back to original file if not a valid/supported image (e.g. video files).
    """
    try:
        # Seek to start
        uploaded_file.seek(0)
        img = PILImage.open(uploaded_file)
        fmt = img.format if img.format else 'JPEG'

        # Resize huge images (max 2048px)
        max_size = 2048
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), PILImage.Resampling.LANCZOS)

        out_io = io.BytesIO()
        if fmt == 'JPEG':
            if img.mode in ('RGBA', 'LA'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            img.save(out_io, format='JPEG', quality=85, optimize=True)
        elif fmt == 'PNG':
            img.save(out_io, format='PNG', optimize=True)
        else:
            img.save(out_io, format=fmt)

        optimized_content = ContentFile(out_io.getvalue())
        optimized_content.name = uploaded_file.name
        return optimized_content
    except Exception:
        # Return fallback file for video or unsupported types
        uploaded_file.seek(0)
        return uploaded_file


def extract_zip_files(zip_file):
    """
    Extracts files from a uploaded zip file, returning a list of (filename, ContentFile).
    """
    extracted = []
    try:
        zip_file.seek(0)
        z = zipfile.ZipFile(zip_file)
        for info in z.infolist():
            # Skip directories
            if info.is_dir():
                continue
            # Skip system files like __MACOSX
            if '__MACOSX' in info.filename or info.filename.split('/')[-1].startswith('.'):
                continue

            # Read bytes
            data = z.read(info.filename)
            cleaned_name = info.filename.split('/')[-1]
            content_file = ContentFile(data)
            content_file.name = cleaned_name
            extracted.append((cleaned_name, content_file))
    except Exception:
        logger.exception("Failed to extract zip file")
    return extracted


def process_file_or_volume(file_obj, filename, image_set, user, created_images):
    """
    Processes a single file. If it's a medical image volume, extracts slices.
    If it's TIFF/BMP/GIF, converts/extracts frames.
    Saves new Image objects.
    """
    # 1. Handle Medical Formats (DICOM, NIfTI, NRRD, MetaImage)
    if is_medical(filename):
        try:
            slices, metadata = convert_medical_file(file_obj, filename)
            # Save metadata to ImageSet
            if metadata:
                if not image_set.metadata:
                    image_set.metadata = {}
                # Merge metadata
                image_set.metadata.update(metadata)
                image_set.save()

            for slice_name, png_bytes in slices:
                content = ContentFile(png_bytes)
                content.name = slice_name
                image = Image.objects.create(
                    user=user,
                    image_set=image_set,
                    file=content,
                    filename=slice_name,
                )
                created_images.append(image)
            return True
        except Exception:
            logger.exception(f"Failed medical conversion for {filename}")
            # Fall back to regular storage
            file_obj.seek(0)

    # 2. Handle animated GIF (frame extraction)
    elif filename.lower().endswith('.gif'):
        try:
            file_obj.seek(0)
            img = PILImage.open(file_obj)
            frames = []
            try:
                while True:
                    frames.append(img.copy())
                    img.seek(img.tell() + 1)
            except EOFError:
                pass

            if len(frames) > 1:
                base = filename.rsplit('.', 1)[0]
                for i, frame in enumerate(frames):
                    out_io = io.BytesIO()
                    frame_rgb = frame.convert('RGB')
                    frame_rgb.save(out_io, format='PNG', optimize=True)
                    slice_name = f"{base}_frame{i + 1:04d}.png"

                    content = ContentFile(out_io.getvalue())
                    content.name = slice_name
                    image = Image.objects.create(
                        user=user,
                        image_set=image_set,
                        file=content,
                        filename=slice_name,
                    )
                    created_images.append(image)
                return True
            file_obj.seek(0)
        except Exception:
            logger.exception(f"Failed animated GIF extraction for {filename}")
            file_obj.seek(0)

    # 3. Handle standard images that need browser conversion (TIFF, BMP)
    elif needs_browser_conversion(filename):
        try:
            file_obj.seek(0)
            img = PILImage.open(file_obj)
            out_io = io.BytesIO()
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                img = img.convert('RGBA')
                img.save(out_io, format='PNG', optimize=True)
            else:
                img = img.convert('RGB')
                img.save(out_io, format='PNG', optimize=True)

            base = filename.rsplit('.', 1)[0]
            slice_name = f"{base}.png"
            content = ContentFile(out_io.getvalue())
            content.name = slice_name
            image = Image.objects.create(
                user=user,
                image_set=image_set,
                file=content,
                filename=slice_name,
            )
            created_images.append(image)
            return True
        except Exception:
            logger.exception(f"Failed TIFF/BMP conversion for {filename}")
            file_obj.seek(0)

    # 4. Handle regular image/video (PNG, JPEG, WEBP, MP4, etc.)
    optimized_f = optimize_uploaded_image(file_obj)
    
    # If the returned file object is a raw BytesIO (or similar) without a name, wrap it
    if not hasattr(optimized_f, 'name') or not optimized_f.name:
        if hasattr(optimized_f, 'seek'):
            optimized_f.seek(0)
        data = optimized_f.read() if hasattr(optimized_f, 'read') else optimized_f
        content = ContentFile(data)
        content.name = filename
        optimized_f = content

    image = Image.objects.create(
        user=user,
        image_set=image_set,
        file=optimized_f,
        filename=filename,
    )
    created_images.append(image)
    return True


class ImageSetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ImageSets.
    Scoped to the authenticated user.
    """
    serializer_class = ImageSetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ImageSet.objects.filter(user=self.request.user).prefetch_related('images__annotations')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for uploaded images.
    Supports listing, retrieving (with annotations), and deleting.
    """

    serializer_class = ImageSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Image.objects.filter(user=self.request.user).prefetch_related('annotations')

    def create(self, request, *args, **kwargs):
        """
        Handle single/multiple/ZIP/folder image uploads, grouping them into an ImageSet.

        POST /api/annotations/images/
        Body: multipart form with 'files' field(s) and optional 'set_id'
        """
        files = request.FILES.getlist('files')
        if not files:
            # Fallback: try single 'file' field
            single_file = request.FILES.get('file')
            if single_file:
                files = [single_file]
            else:
                return Response(
                    {'error': 'No files provided.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Flatten zip files if uploaded
        flat_files = []
        for f in files:
            if f.name.lower().endswith('.zip'):
                extracted = extract_zip_files(f)
                for name, data in extracted:
                    flat_files.append((name, data))
            else:
                flat_files.append((f.name, f))

        if not flat_files:
            return Response(
                {'error': 'No valid files found.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        set_id = request.data.get('set_id')
        image_set = None

        if set_id:
            try:
                image_set = ImageSet.objects.get(id=set_id, user=request.user)
            except ImageSet.DoesNotExist:
                return Response(
                    {'error': f'ImageSet with id {set_id} not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            # Generate a new default name using the timestamp or name of the first file
            import datetime
            time_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            first_name = flat_files[0][0].rsplit('.', 1)[0]
            set_name = f"Set: {first_name} ({time_str})"
            image_set = ImageSet.objects.create(user=request.user, name=set_name)

        created_images = []
        for name, file_obj in flat_files:
            process_file_or_volume(file_obj, name, image_set, request.user, created_images)

        # Update the timestamp on the image_set to push it to the top
        image_set.save()

        serializer = self.get_serializer(created_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AnnotationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for polygon annotations on images.
    Scoped to images owned by the authenticated user.
    """

    serializer_class = AnnotationSerializer

    def get_queryset(self):
        return Annotation.objects.filter(
            image__user=self.request.user
        ).select_related('image')

    def perform_create(self, serializer):
        # Verify the image belongs to the current user
        image = serializer.validated_data.get('image')
        if image.user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You do not own this image.')
        serializer.save()
