from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0003_movie_processing_fields"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="movie",
            index=models.Index(fields=["-uploaded_at"], name="movie_uploaded_at_idx"),
        ),
        migrations.AddIndex(
            model_name="movie",
            index=models.Index(fields=["processing_status", "-uploaded_at"], name="movie_status_uploaded_idx"),
        ),
    ]
