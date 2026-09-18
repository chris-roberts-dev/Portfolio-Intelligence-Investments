# Generated for the Phase 5 historical rebalancing comparison foundation.

import decimal
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rebalancing", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalRebalanceComparison",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("period_start", models.DateField()),
                ("period_end", models.DateField()),
                ("provider", models.CharField(max_length=32)),
                ("price_field", models.CharField(default="adjusted_close", max_length=32)),
                ("retrieved_at", models.DateTimeField(blank=True, null=True)),
                ("drift_threshold", models.DecimalField(decimal_places=12, max_digits=18)),
                (
                    "commission_rate",
                    models.DecimalField(
                        decimal_places=12,
                        default=decimal.Decimal("0"),
                        max_digits=18,
                    ),
                ),
                (
                    "slippage_rate",
                    models.DecimalField(
                        decimal_places=12,
                        default=decimal.Decimal("0"),
                        max_digits=18,
                    ),
                ),
                ("engine_version", models.CharField(max_length=64)),
                ("result", models.JSONField()),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "portfolio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historical_rebalance_comparisons",
                        to="portfolios.portfolio",
                    ),
                ),
                (
                    "target_allocation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="historical_rebalance_comparisons",
                        to="rebalancing.targetallocation",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="historical_rebalance_comparisons",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at", "id")},
        ),
    ]
