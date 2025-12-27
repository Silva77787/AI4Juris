from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_group_name_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="group",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="documents",
                to="api.group",
            ),
        ),
        migrations.AlterField(
            model_name="document",
            name="state",
            field=models.CharField(
                choices=[
                    ("QUEUED", "Queued"),
                    ("PROCESSING", "Processing"),
                    ("DONE", "Done"),
                    ("ERROR", "Error"),
                    ("TIMEOUT", "Timeout"),
                ],
                default="QUEUED",
                max_length=20,
            ),
        ),
    ]
