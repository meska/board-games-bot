# Generated by Django 4.0.5 on 2022-06-16 17:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='weeklypollanswer',
            name='user_name',
        ),
    ]
