from django import forms
from .models import Movie
from moviepy.video.io.VideoFileClip import VideoFileClip
import os
import tempfile
from django.conf import settings

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'video_file']

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')

        if video_file:
            # 파일 용량 제한 (1GB 이하)
            if video_file.size > 1 * 1024 * 1024 * 1024:
                raise forms.ValidationError('파일 크기는 1GB 이하이어야 합니다.')

            # 임시 파일 경로 (Windows 및 Unix 환경 모두 처리)
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file_path = temp_file.name

            # 파일을 임시 파일로 저장
            with open(temp_file_path, 'wb+') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)

            # 비디오 파일을 MP4로 인코딩
            clip = VideoFileClip(temp_file_path)
            output_file_path = os.path.join(settings.MEDIA_ROOT, 'videos', video_file.name)

            # 비디오 파일 저장
            clip.write_videofile(output_file_path, codec='libx264')

            # 인코딩된 파일로 대체
            video_file.name = os.path.join('videos', os.path.basename(output_file_path))

            # 임시 파일 정리
            os.remove(temp_file_path)

        return video_file
