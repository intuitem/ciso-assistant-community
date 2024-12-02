# Generated by Django 5.1.1 on 2024-12-02 17:01

import django.db.models.deletion
import iam.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_historicalmetric'),
        ('iam', '0009_create_allauth_emailaddress_objects'),
    ]

    operations = [
        migrations.CreateModel(
            name='Qualification',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated at')),
                ('is_published', models.BooleanField(default=False, verbose_name='published')),
                ('urn', models.CharField(blank=True, max_length=255, null=True, unique=True, verbose_name='URN')),
                ('ref_id', models.CharField(blank=True, max_length=100, null=True, verbose_name='Reference ID')),
                ('provider', models.CharField(blank=True, max_length=200, null=True, verbose_name='Provider')),
                ('name', models.CharField(max_length=200, null=True, verbose_name='Name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('annotation', models.TextField(blank=True, null=True, verbose_name='Annotation')),
                ('translations', models.JSONField(blank=True, null=True, verbose_name='Translations')),
                ('locale', models.CharField(default='en', max_length=100, verbose_name='Locale')),
                ('default_locale', models.BooleanField(default=True, verbose_name='Default locale')),
                ('abbreviation', models.CharField(blank=True, max_length=20, null=True, verbose_name='Abbreviation')),
                ('qualification_ordering', models.PositiveSmallIntegerField(default=0, verbose_name='Ordering')),
                ('security_objective_ordering', models.PositiveSmallIntegerField(default=0, verbose_name='Security objective ordering')),
                ('folder', models.ForeignKey(default=iam.models.Folder.get_root_folder_id, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_folder', to='iam.folder')),
            ],
            options={
                'verbose_name': 'Qualification',
                'verbose_name_plural': 'Qualifications',
                'ordering': ['qualification_ordering'],
            },
        ),
    ]