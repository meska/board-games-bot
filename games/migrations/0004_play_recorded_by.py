# Generated by Django 4.0.5 on 2022-06-18 13:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bot', '0001_initial'),
        ('games', '0003_alter_game_thumbnail'),
    ]

    operations = [
        migrations.AddField(
            model_name='play',
            name='recorded_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bot.user'),
        ),
    ]
