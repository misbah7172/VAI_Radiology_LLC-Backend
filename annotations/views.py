from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Image, Annotation, ImageSet
from .serializers import ImageSerializer, AnnotationSerializer, ImageSetSerializer


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
        Handle single or multiple image uploads, grouping them into an ImageSet.

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
            first_name = files[0].name.split('.')[0]
            set_name = f"Set: {first_name} ({time_str})"
            image_set = ImageSet.objects.create(user=request.user, name=set_name)

        created_images = []
        for f in files:
            image = Image.objects.create(
                user=request.user,
                image_set=image_set,
                file=f,
                filename=f.name,
            )
            created_images.append(image)

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
