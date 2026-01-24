from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_document_storage_path_and_page_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="classification",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="document",
            name="justification",
            field=models.TextField(blank=True, null=True),
        ),
    ]
