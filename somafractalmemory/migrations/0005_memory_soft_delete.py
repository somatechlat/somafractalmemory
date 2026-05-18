"""Add soft delete fields to Memory model."""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Migration class implementation."""

    dependencies = [
        ("somafractalmemory", "0004_apikey_usagerecord"),
    ]

    operations = [
        migrations.AddField(
            model_name="memory",
            name="is_deleted",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="memory",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
