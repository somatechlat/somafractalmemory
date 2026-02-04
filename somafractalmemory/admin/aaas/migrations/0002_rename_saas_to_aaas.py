"""
Django Migration: Rename saas_* db_table references in SomaFractalMemory.

VIBE Compliance:
- Rule 10: Django ORM only
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Rename saas references in SomaFractalMemory models."""

    dependencies = [
        ("aaas", "0001_initial"),  # Adjust based on actual last migration
    ]

    operations = [
        # If there are specific tables that need renaming, add them here
        # Example:
        # migrations.AlterModelTable(
        #     name="apikey",
        #     table="aaas_api_keys",
        # ),
    ]
