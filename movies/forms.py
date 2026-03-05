import os

from django import forms

from .models import Movie

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
MAX_UPLOAD_SIZE_MB = 1024


class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ["title", "description", "video_file"]

    def clean_video_file(self):
        video = self.cleaned_data.get("video_file")
        if not video:
            return video

        ext = os.path.splitext(video.name)[1].lower()
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise forms.ValidationError(
                "지원하지 않는 파일 형식입니다. mp4, mov, m4v, webm, mkv만 업로드할 수 있습니다."
            )

        content_type = getattr(video, "content_type", "") or ""
        if not content_type.startswith("video/"):
            raise forms.ValidationError("영상 파일만 업로드할 수 있습니다.")

        max_size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if video.size > max_size:
            raise forms.ValidationError(f"파일 크기는 {MAX_UPLOAD_SIZE_MB}MB 이하여야 합니다.")

        return video
