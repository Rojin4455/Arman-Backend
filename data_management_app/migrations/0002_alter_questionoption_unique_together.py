# Generated by Django 5.2.1 on 2025-06-17 16:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_management_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='questionoption',
            unique_together=set(),
        ),
    ]
