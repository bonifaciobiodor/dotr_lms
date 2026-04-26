"""
Server-side file upload validators that inspect actual file content (magic bytes)
rather than trusting the browser-supplied Content-Type header.
"""

# Magic-byte signatures: (offset, bytes)
_IMAGE_SIGNATURES = {
    'jpeg': [(0, b'\xff\xd8\xff')],
    'png':  [(0, b'\x89PNG\r\n\x1a\n')],
    'gif':  [(0, b'GIF87a'), (0, b'GIF89a')],
    'webp': [(0, b'RIFF'), (8, b'WEBP')],
}

_MODULE_SIGNATURES = {
    'pdf':  [(0, b'%PDF')],
    'zip':  [(0, b'PK\x03\x04')],   # docx, pptx, xlsx are ZIP-based
    'mp4':  [(4, b'ftyp')],
    'webm': [(0, b'\x1aE\xdf\xa3')],
    'mpeg': [(0, b'\xff\xfb'), (0, b'\xff\xf3'), (0, b'\xff\xf2'), (0, b'ID3')],
}

_MAX_READ = 16


def _matches(buf: bytes, signatures: list) -> bool:
    for offset, magic in signatures:
        if buf[offset: offset + len(magic)] == magic:
            return True
    return False


def _detect_image(buf: bytes) -> bool:
    for sigs in _IMAGE_SIGNATURES.values():
        if _matches(buf, sigs):
            return True
    return False


def _detect_module_file(buf: bytes) -> bool:
    for sigs in _MODULE_SIGNATURES.values():
        if _matches(buf, sigs):
            return True
    return False


def validate_image_upload(upload):
    """
    Raise ValueError if the upload is not a JPEG, PNG, GIF, or WebP.
    Reads the first 16 bytes and checks magic bytes; rewinds the file afterward.
    """
    buf = upload.read(_MAX_READ)
    upload.seek(0)
    if not _detect_image(buf):
        raise ValueError(
            'Uploaded file is not a valid image (JPEG, PNG, GIF, or WebP). '
            'The file content does not match any supported image format.'
        )
    if upload.size > 2 * 1024 * 1024:
        raise ValueError(f'Image too large ({upload.size // 1024} KB). Maximum is 2 MB.')


def validate_module_file(upload):
    """
    Raise ValueError if a training module file is not a recognised safe type:
    PDF, Office document (DOCX/PPTX/XLSX via ZIP), MP4, WebM, or MP3.
    Max size: 200 MB.
    """
    buf = upload.read(_MAX_READ)
    upload.seek(0)
    if not _detect_module_file(buf):
        raise ValueError(
            'Uploaded file type is not allowed. '
            'Supported types: PDF, DOCX/PPTX/XLSX, MP4, WebM, MP3.'
        )
    max_bytes = 200 * 1024 * 1024
    if upload.size > max_bytes:
        raise ValueError(f'File too large ({upload.size // (1024 * 1024)} MB). Maximum is 200 MB.')
