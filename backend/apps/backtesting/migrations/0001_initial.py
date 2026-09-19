# Generated for Phase 6 persisted backtest runs.

import uuid
from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BacktestRun",
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
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("RUNNING", "Running"),
                            ("SUCCEEDED", "Succeeded"),
                            ("FAILED", "Failed"),
                        ],
                        default="PENDING",
                        max_length=16,
                    ),
                ),
                (
                    "strategy",
                    models.CharField(
                        choices=[("BUY_AND_HOLD", "Buy and hold")],
                        default="BUY_AND_HOLD",
                        max_length=32,
                    ),
                ),
                ("period_start", models.DateField()),
                ("period_end_exclusive", models.DateField()),
                ("provider", models.CharField(max_length=32)),
                (
                    "price_field",
                    models.CharField(default="adjusted_close", max_length=32),
                ),
                ("included_asset_ids", models.JSONField(default=list)),
                ("parameters", models.JSONField(default=dict)),
                ("initial_cash", models.DecimalField(decimal_places=8, max_digits=24)),
                (
                    "commission_rate",
                    models.DecimalField(
                        decimal_places=12,
                        default=Decimal("0"),
                        max_digits=18,
                    ),
                ),
                (
                    "slippage_rate",
                    models.DecimalField(
                        decimal_places=12,
                        default=Decimal("0"),
                        max_digits=18,
                    ),
                ),
                ("result", models.JSONField(blank=True, null=True)),
                ("warnings", models.JSONField(blank=True, default=list)),
                ("engine_version", models.CharField(default="0.2.0", max_length=64)),
                ("method_version", models.CharField(default="1.0", max_length=32)),
                ("strategy_version", models.CharField(default="1.0", max_length=32)),
                ("data_retrieved_at", models.DateTimeField(blank=True, null=True)),
                ("data_fingerprint", models.CharField(blank=True, max_length=64)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("failure_message", models.TextField(blank=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backtest_runs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ("-created_at", "id")},
        ),
    ]
