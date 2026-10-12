# somafractalmemory/migrations/0009_memory_belief_fields_and_working_memory.py
# B19 + D1: belief semantics as first-class columns; working_memory in the
# type vocabulary so WM persistence is not rejected at the contract boundary.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("somafractalmemory", "0008_memory_type_belief_and_namespace_belief_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="memory",
            name="belief_confidence",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="memory",
            name="belief_polarity",
            field=models.CharField(
                blank=True,
                default="",
                help_text="positive | negative | unknown — empty for non-belief rows",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="memory",
            name="memory_type",
            field=models.CharField(
                choices=[
                    ("episodic", "Episodic"),
                    ("semantic", "Semantic"),
                    ("belief", "Belief"),
                    ("working_memory", "Working Memory"),
                ],
                default="episodic",
                max_length=20,
            ),
        ),
    ]
