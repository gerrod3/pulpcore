# Generated by Django 4.2.16 on 2025-02-03 16:41

import django.contrib.postgres.fields.hstore
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0127_remove_upstreampulp_pulp_label_select"),
    ]

    operations = [
        migrations.AddField(
            model_name="domain",
            name="pulp_labels",
            field=django.contrib.postgres.fields.hstore.HStoreField(default=dict),
        ),
    ]
