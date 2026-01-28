from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("somafractalmemory", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="memory",
            name="unique_namespace_coordinate",
        ),
        migrations.AddConstraint(
            model_name="memory",
            constraint=models.UniqueConstraint(
                fields=("namespace", "tenant", "coordinate_key"),
                name="unique_namespace_tenant_coordinate",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="graphlink",
            name="unique_graph_link",
        ),
        migrations.AddConstraint(
            model_name="graphlink",
            constraint=models.UniqueConstraint(
                fields=(
                    "namespace",
                    "tenant",
                    "from_coordinate_key",
                    "to_coordinate_key",
                    "link_type",
                ),
                name="unique_graph_link_tenant",
            ),
        ),
    ]
