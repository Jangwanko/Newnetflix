# movies/forms.py
from django import forms
from .models import Movie
from moviepy.video.io.VideoFileClip import VideoFileClip
import os

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'genre', 'year', 'video_file']

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')

        if video_file:
            # 파일 용량 제한 (1GB 이하)
            if video_file.size > 1 * 1024 * 1024 * 1024:
                raise forms.ValidationError('파일 크기는 1GB 이하이어야 합니다.')

            # 임시 파일 경로
            temp_file_path = os.path.join('/tmp', video_file.name)
            with open(temp_file_path, 'wb+') as temp_file:
                for chunk in video_file.chunks():
                    temp_file.write(chunk)

            # 비디오 파일을 MP4로 인코딩
            clip = VideoFileClip(temp_file_path)
            output_file_path = os.path.splitext(temp_file_path)[0] + '.mp4'
            clip.write_videofile(output_file_path, codec='libx264')

            # 인코딩된 파일로 대체
            with open(output_file_path, 'rb') as output_file:
                video_file.file = output_file.read()
                video_file.name = os.path.basename(output_file_path)

        return video_file
