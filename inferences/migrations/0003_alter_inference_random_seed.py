# Generated by Django 4.2.19 on 2025-03-26 02:00

from django.db import migrations, models
import inferences.models


class Migration(migrations.Migration):

    dependencies = [
        ('inferences', '0002_alter_inference_dta_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inference',
            name='random_seed',
            field=models.PositiveIntegerField(blank=True, default=inferences.models.generate_random_seed, null=True),
        ),
    ]
