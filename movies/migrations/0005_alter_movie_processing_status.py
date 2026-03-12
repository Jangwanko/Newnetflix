from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("movies", "0004_movie_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="movie",
            name="processing_status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("processing", "Processing"),
                    ("ready", "Ready"),
                    ("failed", "Failed"),
                ],
                default="ready",
                max_length=20,
            ),
        ),
    ]
