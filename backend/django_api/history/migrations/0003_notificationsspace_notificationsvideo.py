from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0002_alter_fcmtoken_token'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationsSpace',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('code', models.CharField(max_length=100)),
                ('city', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('organization_id', models.BigIntegerField()),
            ],
            options={
                'db_table': 'notifications_space',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='NotificationsVideo',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('path', models.CharField(max_length=255)),
                ('code', models.CharField(max_length=100)),
                ('status', models.CharField(max_length=30)),
                ('probability', models.FloatField(null=True)),
                ('recording_date', models.DateTimeField()),
                ('create_date', models.DateTimeField()),
                ('camera_id', models.BigIntegerField()),
                ('qualification', models.CharField(max_length=50, null=True)),
                ('sub_status', models.CharField(max_length=30)),
                ('nb_alerts', models.IntegerField(null=True)),
            ],
            options={
                'db_table': 'notifications_video',
                'managed': False,
            },
        ),
    ]