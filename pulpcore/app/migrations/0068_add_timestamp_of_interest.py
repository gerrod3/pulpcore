# Generated by Django 2.2.20 on 2021-05-07 18:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0067_add_protect_to_task_reservation'),
    ]

    operations = [
        migrations.AddField(
            model_name='artifact',
            name='timestamp_of_interest',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='content',
            name='timestamp_of_interest',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
