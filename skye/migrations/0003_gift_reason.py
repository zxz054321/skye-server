# Generated by Django 3.2.16 on 2023-01-20 07:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skye', '0002_alter_profile_inviter'),
    ]

    operations = [
        migrations.AddField(
            model_name='gift',
            name='reason',
            field=models.CharField(default='', max_length=20),
        ),
    ]
