import imageio_ffmpeg


def ffmpeg_exe():
    """Return the FFmpeg executable managed by imageio-ffmpeg."""
    return imageio_ffmpeg.get_ffmpeg_exe()
