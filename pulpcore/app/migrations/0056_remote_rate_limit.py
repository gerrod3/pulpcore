# Generated by Django 2.2.17 on 2021-01-27 18:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0055_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='remote',
            name='rate_limit',
            field=models.IntegerField(null=True),
        ),
    ]
