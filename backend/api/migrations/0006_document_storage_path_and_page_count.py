from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_document_group_and_state_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="page_count",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="storage_path",
            field=models.CharField(blank=True, max_length=512),
        ),
    ]
