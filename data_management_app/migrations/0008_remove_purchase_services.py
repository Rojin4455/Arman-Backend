# Generated by Django 5.2.1 on 2025-06-18 07:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('data_management_app', '0007_remove_purchasedservice_price_plan_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='purchase',
            name='services',
        ),
    ]
