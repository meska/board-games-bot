# Generated by Django 4.0.5 on 2022-06-16 13:22

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('bot', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WeeklyPoll',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('poll_id', models.BigIntegerField(blank=True, null=True)),
                ('message_id', models.BigIntegerField(blank=True, null=True)),
                ('weekday', models.IntegerField(blank=True, null=True)),
                ('lang', models.CharField(default='en', max_length=5)),
                ('question_prefix', models.CharField(default='', max_length=200)),
                ('answers', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), default=list, size=None)),
                ('poll_date', models.DateField(blank=True, null=True)),
                ('chat', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='bot.chat')),
            ],
        ),
        migrations.CreateModel(
            name='WeeklyPollAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.IntegerField(blank=True, choices=[(0, 'Yes'), (1, 'No')], null=True)),
                ('user_name', models.CharField(blank=True, max_length=200, null=True)),
                ('answer_date', models.DateTimeField(auto_now=True, verbose_name='date answered')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bot.user')),
                ('wp', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='polls.weeklypoll')),
            ],
        ),
    ]
