# ============================================================
# migrations/0003_notification.py
# backend/django_api/migrations/0003_notification.py
# ============================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0002_notificationlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('generated_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.TextField()),
                ('visiteurs_prevus', models.IntegerField(default=0)),
                ('profil_dominant', models.CharField(default='', max_length=255)),
                ('niveau_affluence', models.CharField(default='', max_length=100)),
                ('heure_pointe', models.CharField(default='', max_length=10)),
                ('model', models.CharField(default='llama3.2:3b-instruct-q4_K_M', max_length=255)),
                ('type', models.CharField(default='prediction', max_length=50)),
                ('is_read', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Notification de prédiction',
                'verbose_name_plural': 'Notifications de prédictions',
                'ordering': ['-generated_at'],
            },
        ),
    ]