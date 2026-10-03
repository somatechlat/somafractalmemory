"""Drop the billing/usage metering tables.

``sfm_api_keys`` and ``sfm_usage_records`` were the product surface: API-key
CRUD and hour-bucketed usage metering that existed to feed a billing sync.
Neither is part of the memory service. The live authentication boundary is
``somafractalmemory.api.auth.StandaloneAuth`` (a Vault-managed bearer token,
constant-time compare, fail-closed when unset), and namespace authorisation is
``api.auth.can_access_namespace``.

``tenant_id`` on the memory tables is untouched by this migration: it is a
data-partition key, not product tenancy.
"""

from django.db import migrations


class Migration(migrations.Migration):
    """Drop the product metering tables created by 0004."""

    dependencies = [
        ("somafractalmemory", "0005_memory_soft_delete"),
    ]

    operations = [
        migrations.DeleteModel(name="UsageRecord"),
        migrations.DeleteModel(name="APIKey"),
    ]
