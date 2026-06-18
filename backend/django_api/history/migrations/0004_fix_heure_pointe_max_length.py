from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('history', '0003_notification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='heure_pointe',
            field=models.CharField(default='', max_length=50),
        ),
    ]