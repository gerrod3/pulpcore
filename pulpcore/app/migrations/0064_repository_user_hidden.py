# Generated by Django 2.2.19 on 2021-04-01 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_repository_retained_versions'),
    ]

    operations = [
        migrations.AddField(
            model_name='repository',
            name='user_hidden',
            field=models.BooleanField(default=False),
        ),
    ]
