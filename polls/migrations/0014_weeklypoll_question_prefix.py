# Generated by Django 4.0.5 on 2022-06-13 21:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polls', '0013_weeklypoll_language'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklypoll',
            name='question_prefix',
            field=models.CharField(default='', max_length=200),
        ),
    ]
