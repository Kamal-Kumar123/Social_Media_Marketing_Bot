"""
A simplified replacement for the removed imghdr module.
This provides just enough functionality to satisfy tweepy's requirements.
"""

def what(file, h=None):
    """
    Determine the type of image contained in a file or byte stream.
    
    This is a simplified version that tries to determine common image formats
    based on their headers.
    
    Args:
        file: A filename (string), a file object, or a bytes-like object.
        h: An optional bytes object containing the header of the file.
    
    Returns:
        A string describing the image type, or None if the type cannot be determined.
    """
    if h is None:
        if isinstance(file, str):
            with open(file, 'rb') as f:
                h = f.read(32)
        else:
            location = file.tell()
            h = file.read(32)
            file.seek(location)
            
    if h.startswith(b'\xff\xd8'):
        return 'jpeg'
    elif h.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    elif h.startswith(b'GIF87a') or h.startswith(b'GIF89a'):
        return 'gif'
    elif h.startswith(b'RIFF') and h[8:12] == b'WEBP':
        return 'webp'
    elif h.startswith(b'BM'):
        return 'bmp'
    return None 