# Generated from Studio.OS isolated domain model design.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="Organization", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)),
            ("currency", models.CharField(default="KES", max_length=3)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
        ]),
        migrations.CreateModel(name="Membership", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("role", models.CharField(choices=[("OWNER", "Owner"), ("COORDINATOR", "Coordinator"), ("DESIGNER", "Designer"), ("FIELD", "Field")], max_length=20)),
            ("active", models.BooleanField(default=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="operations.organization")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ], options={"constraints": [models.UniqueConstraint(fields=("organization", "user"), name="unique_org_membership")]}),
        migrations.CreateModel(name="Customer", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=180)),
            ("email", models.EmailField(blank=True, max_length=254)),
            ("phone", models.CharField(blank=True, max_length=40)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="operations.organization")),
        ]),
        migrations.CreateModel(name="Lead", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("brief", models.TextField(blank=True)),
            ("status", models.CharField(choices=[("NEW", "New"), ("CONTACTED", "Contacted"), ("QUALIFIED", "Qualified"), ("CONSULTATION_BOOKED", "Consultation Booked"), ("ASSESSED", "Assessed"), ("QUOTED", "Quoted"), ("WON", "Won"), ("LOST", "Lost"), ("DORMANT", "Dormant")], default="NEW", max_length=24)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="leads", to="operations.customer")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="operations.organization")),
        ]),
        migrations.CreateModel(name="Activity", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(max_length=64)),
            ("details", models.JSONField(default=dict)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("actor", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ("lead", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to="operations.lead")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="operations.organization")),
        ]),
        migrations.CreateModel(name="NextAction", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("title", models.CharField(max_length=180)),
            ("due_at", models.DateTimeField(blank=True, null=True)),
            ("done", models.BooleanField(default=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("assignee", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ("lead", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="actions", to="operations.lead")),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="operations.organization")),
        ]),
    ]
