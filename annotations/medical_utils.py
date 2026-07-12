"""
Medical imaging format conversion utilities.

Converts DICOM, NIfTI, NRRD, and MetaImage volumes into PNG slice sequences
that are compatible with the existing ImageSet / Image storage model.

Required packages (in requirements.txt):
    pydicom   >= 2.4   — DICOM file reading
    SimpleITK >= 2.4   — NIfTI / NRRD / MHA / MHD volume reading
    numpy     >= 1.24  — Array operations
    Pillow    >= 10.4  — Frame → PNG conversion (already required)
"""

import io
import logging
import os
import tempfile

import numpy as np
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# ── Extension classification ───────────────────────────────────────────────────
DICOM_EXTS = frozenset(['.dcm', '.dicom'])
NIFTI_EXTS = frozenset(['.nii', '.nii.gz'])
NRRD_EXTS  = frozenset(['.nrrd', '.nhdr'])
MHA_EXTS   = frozenset(['.mha', '.mhd'])
SITK_EXTS  = NIFTI_EXTS | NRRD_EXTS | MHA_EXTS
MEDICAL_EXTS = DICOM_EXTS | SITK_EXTS

# Standard image extensions that browsers can render natively
TIFF_EXTS  = frozenset(['.tif', '.tiff'])
BMP_EXTS   = frozenset(['.bmp', '.dib'])
GIF_EXTS   = frozenset(['.gif'])
NEEDS_CONVERSION = TIFF_EXTS | BMP_EXTS | GIF_EXTS


def get_ext(filename: str) -> str:
    """
    Return the lower-case extension of a filename.
    Treats '.nii.gz' as a single two-part extension.
    """
    fn = filename.lower()
    if fn.endswith('.nii.gz'):
        return '.nii.gz'
    _, ext = os.path.splitext(fn)
    return ext


def is_medical(filename: str) -> bool:
    """Return True if the filename has a recognised medical imaging extension."""
    return get_ext(filename) in MEDICAL_EXTS


def needs_browser_conversion(filename: str) -> bool:
    """Return True for formats that require server-side conversion for browser compatibility."""
    return get_ext(filename) in NEEDS_CONVERSION


# ── Array normalisation ────────────────────────────────────────────────────────

def _normalize(arr: np.ndarray) -> np.ndarray:
    """Linearly map any numeric array to uint8 [0, 255]."""
    arr = arr.astype(np.float32)
    mn, mx = float(arr.min()), float(arr.max())
    if mx == mn:
        return np.zeros_like(arr, dtype=np.uint8)
    return ((arr - mn) / (mx - mn) * 255.0).astype(np.uint8)


def _frame_to_png_bytes(frame: np.ndarray) -> bytes:
    """Convert a 2-D (grayscale) or 3-D (RGB/RGBA) numpy array to PNG bytes."""
    norm = _normalize(frame)
    if norm.ndim == 2:
        img = PILImage.fromarray(norm, mode='L').convert('RGB')
    else:
        img = PILImage.fromarray(norm)
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return buf.getvalue()


def _base_name(filename: str) -> str:
    """Strip the medical file extension and return the stem."""
    for ext in ('.nii.gz', '.nii', '.nrrd', '.nhdr', '.mha', '.mhd',
                '.dcm', '.dicom'):
        if filename.lower().endswith(ext):
            return filename[: len(filename) - len(ext)]
    root, _ = os.path.splitext(filename)
    return root


# ── DICOM ──────────────────────────────────────────────────────────────────────

def convert_dicom(file_obj, filename: str):
    """
    Convert a DICOM file (single-frame or multi-frame) to PNG slices.

    Parameters
    ----------
    file_obj : file-like   — seekable binary file object
    filename : str         — original filename (used to derive slice names)

    Returns
    -------
    slices   : list of (slice_filename: str, png_bytes: bytes)
    metadata : dict — serialisable DICOM tag values
    """
    import pydicom  # noqa: import-error (optional dep)

    file_obj.seek(0)
    ds = pydicom.dcmread(file_obj, force=True)
    pixel_array = ds.pixel_array.astype(np.float32)

    # Apply Rescale if present (e.g. HU values in CT)
    slope     = float(getattr(ds, 'RescaleSlope',     1.0))
    intercept = float(getattr(ds, 'RescaleIntercept', 0.0))
    pixel_array = pixel_array * slope + intercept

    base = _base_name(filename)
    frames = [pixel_array] if pixel_array.ndim == 2 else list(pixel_array)

    slices = []
    for i, frame in enumerate(frames):
        png = _frame_to_png_bytes(frame)
        fname = (
            f"{base}.png"
            if len(frames) == 1
            else f"{base}_slice{i + 1:04d}.png"
        )
        slices.append((fname, png))

    return slices, _dicom_metadata(ds)


def _dicom_metadata(ds) -> dict:
    """Extract key DICOM tag values as a JSON-serialisable dict."""
    TAGS = [
        'PatientName', 'PatientID', 'PatientBirthDate', 'PatientSex',
        'StudyDate', 'StudyTime', 'StudyDescription', 'SeriesDescription',
        'Modality', 'Manufacturer', 'InstitutionName',
        'Rows', 'Columns', 'NumberOfFrames',
        'PixelSpacing', 'SliceThickness',
        'ImageOrientationPatient', 'ImagePositionPatient',
        'BitsAllocated', 'BitsStored', 'PhotometricInterpretation',
    ]
    meta = {}
    for tag in TAGS:
        val = getattr(ds, tag, None)
        if val is not None:
            meta[tag] = str(val)
    return meta


# ── SimpleITK — NIfTI / NRRD / MHA / MHD ─────────────────────────────────────

def convert_sitk(file_obj, filename: str):
    """
    Convert a SimpleITK-readable volume to axial (z-axis) PNG slices.

    Supports .nii, .nii.gz, .nrrd, .nhdr, .mha, .mhd

    Parameters
    ----------
    file_obj : file-like
    filename : str

    Returns
    -------
    slices   : list of (slice_filename: str, png_bytes: bytes)
    metadata : dict
    """
    import SimpleITK as sitk  # noqa: import-error (optional dep)

    ext = get_ext(filename)
    file_obj.seek(0)
    raw = file_obj.read()

    # SimpleITK requires a real filesystem path — write to a temp file
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name

    try:
        image = sitk.ReadImage(tmp_path)
        array = sitk.GetArrayFromImage(image)   # shape: (z, y, x) for 3-D

        if array.ndim == 2:
            array = array[np.newaxis]           # make it (1, y, x)

        base = _base_name(filename)
        n = array.shape[0]
        slices = []

        for i in range(n):
            png = _frame_to_png_bytes(array[i])
            fname = (
                f"{base}.png"
                if n == 1
                else f"{base}_slice{i + 1:04d}.png"
            )
            slices.append((fname, png))

        metadata = {
            'format':   ext.lstrip('.').upper(),
            'size':     list(image.GetSize()),
            'spacing':  [round(s, 4) for s in image.GetSpacing()],
            'origin':   [round(o, 4) for o in image.GetOrigin()],
            'n_slices': n,
        }
        return slices, metadata

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── Master dispatcher ──────────────────────────────────────────────────────────

def convert_medical_file(file_obj, filename: str):
    """
    Convert a medical imaging file into PNG slices.

    Dispatches to the appropriate converter based on the file extension.

    Parameters
    ----------
    file_obj : file-like object (seekable binary)
    filename : str — original filename (determines format)

    Returns
    -------
    slices   : list of (slice_filename: str, png_bytes: bytes)
    metadata : dict

    Raises
    ------
    ValueError   for unrecognised extensions
    RuntimeError on conversion failure (wraps the underlying exception)
    """
    ext = get_ext(filename)

    try:
        if ext in DICOM_EXTS:
            return convert_dicom(file_obj, filename)
        elif ext in SITK_EXTS:
            return convert_sitk(file_obj, filename)
        else:
            raise ValueError(f"Unrecognised medical format extension: {ext!r}")
    except (ValueError, RuntimeError):
        raise
    except ImportError as exc:
        missing_pkg = 'pydicom' if ext in DICOM_EXTS else 'SimpleITK'
        raise RuntimeError(
            f"Cannot convert {filename!r}: {missing_pkg} is not installed. "
            f"Run: pip install {missing_pkg}"
        ) from exc
    except Exception as exc:
        raise RuntimeError(f"Conversion of {filename!r} failed: {exc}") from exc
