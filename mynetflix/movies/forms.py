from django import forms
from .models import Movie
from moviepy.video.io.VideoFileClip import VideoFileClip
from django.conf import settings
import os
import tempfile
from django.core.files import File

class MovieForm(forms.ModelForm):
    class Meta:
        model = Movie
        fields = ['title', 'description', 'video_file']

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if video_file and video_file.size > 1 * 1024 * 1024 * 1024:
            raise forms.ValidationError('파일 크기는 1GB 이하이어야 합니다.')
        return video_file

    def save(self, commit=True):
        instance = super().save(commit=False)
        video_file = self.cleaned_data.get('video_file')

        if video_file:
            # 임시 원본 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(video_file.name)[1]) as temp_orig_file:
                for chunk in video_file.chunks():
                    temp_orig_file.write(chunk)
                temp_orig_path = temp_orig_file.name

            # 인코딩된 파일 임시 경로
            temp_encoded_path = temp_orig_path + '_encoded.mp4'

            # moviepy로 인코딩
            clip = VideoFileClip(temp_orig_path)
            clip.write_videofile(temp_encoded_path, codec='libx264')
            clip.close()

            # 임시 인코딩된 파일을 Django File 객체로 열기
            with open(temp_encoded_path, 'rb') as f:
                django_file = File(f)
                # 파일명은 원본 파일명 또는 원하는 이름으로 지정
                instance.video_file.save(os.path.basename(video_file.name), django_file, save=False)

            # 임시 파일 삭제
            os.remove(temp_orig_path)
            os.remove(temp_encoded_path)

        if commit:
            instance.save()

        return instance
