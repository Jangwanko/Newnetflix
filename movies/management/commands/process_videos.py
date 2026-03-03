import time

from django.core.management.base import BaseCommand
from django.db import OperationalError, transaction

from moviepy import VideoFileClip

from movies.models import Movie


class Command(BaseCommand):
    help = "Process queued videos in the background."

    def add_arguments(self, parser):
        parser.add_argument(
            "--poll-interval",
            type=int,
            default=3,
            help="Seconds to wait when there are no queued videos.",
        )

    def handle(self, *args, **options):
        poll_interval = options["poll_interval"]
        self.stdout.write(self.style.SUCCESS("Video worker started."))

        while True:
            try:
                movie = self._pick_next_movie()
            except OperationalError:
                # DB might not be ready yet; retry until available.
                time.sleep(poll_interval)
                continue

            if movie is None:
                time.sleep(poll_interval)
                continue

            self._process_movie(movie)

    def _pick_next_movie(self):
        with transaction.atomic():
            movie = (
                Movie.objects.select_for_update(skip_locked=True)
                .filter(processing_status=Movie.ProcessingStatus.QUEUED)
                .order_by("uploaded_at")
                .first()
            )
            if not movie:
                return None

            movie.processing_status = Movie.ProcessingStatus.PROCESSING
            movie.processing_error = ""
            movie.save(update_fields=["processing_status", "processing_error"])
            return movie

    def _process_movie(self, movie):
        try:
            with VideoFileClip(movie.video_file.path) as clip:
                duration = float(clip.duration or 0)

            movie.duration_seconds = round(duration, 1)
            movie.processing_status = Movie.ProcessingStatus.READY
            movie.processing_error = ""
            movie.save(update_fields=["duration_seconds", "processing_status", "processing_error"])
            self.stdout.write(self.style.SUCCESS(f"Processed movie #{movie.id}: {movie.title}"))
        except Exception as exc:
            movie.processing_status = Movie.ProcessingStatus.FAILED
            movie.processing_error = str(exc)[:500]
            movie.save(update_fields=["processing_status", "processing_error"])
            self.stderr.write(self.style.ERROR(f"Failed movie #{movie.id}: {exc}"))
