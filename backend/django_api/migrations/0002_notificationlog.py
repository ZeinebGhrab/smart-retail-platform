# ============================================================
# migrations/0002_notificationlog.py
# backend/django_api/migrations/0002_notificationlog.py
# ============================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationLog',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title',       models.CharField(max_length=255)),
                ('body',        models.TextField()),
                ('data',        models.JSONField(default=dict, blank=True)),
                ('sent_at',     models.DateTimeField(auto_now_add=True)),
                ('sent_count',  models.IntegerField(default=0)),
                ('error_count', models.IntegerField(default=0)),
                ('errors',      models.JSONField(default=list, blank=True)),
            ],
            options={
                'verbose_name': 'Notification Log',
                'verbose_name_plural': 'Notification Logs',
                'ordering': ['-sent_at'],
            },
        ),
    ]