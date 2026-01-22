# Generated migration for Questionnaire bounded context

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        # Questionnaire model
        migrations.CreateModel(
            name='Questionnaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('title', models.CharField(help_text='Questionnaire title', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Questionnaire description', null=True)),
                ('questionnaire_type', models.CharField(choices=[('assessment', 'Assessment'), ('survey', 'Survey'), ('audit', 'Audit'), ('compliance', 'Compliance Check'), ('risk', 'Risk Assessment'), ('custom', 'Custom')], default='assessment', help_text='Type of questionnaire', max_length=20)),
                ('category', models.CharField(blank=True, help_text='Questionnaire category (e.g., \'Security\', \'Compliance\')', max_length=100, null=True)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('published', 'Published'), ('archived', 'Archived')], default='draft', help_text='Questionnaire lifecycle status', max_length=20)),
                ('version', models.CharField(default='1.0', help_text='Questionnaire version', max_length=20)),
                ('estimated_duration_minutes', models.IntegerField(blank=True, help_text='Estimated completion time in minutes', null=True)),
                ('is_public', models.BooleanField(default=False, help_text='Whether questionnaire is publicly accessible')),
                ('requires_authentication', models.BooleanField(default=True, help_text='Whether authentication is required')),
                ('enable_scoring', models.BooleanField(default=True, help_text='Whether questionnaire supports scoring')),
                ('passing_score_percentage', models.IntegerField(blank=True, help_text='Minimum passing score percentage (if scoring enabled)', null=True)),
                ('enable_conditional_logic', models.BooleanField(default=True, help_text='Whether conditional question logic is enabled')),
                ('allow_back_navigation', models.BooleanField(default=True, help_text='Whether users can navigate backwards')),
                ('show_progress_bar', models.BooleanField(default=True, help_text='Whether to show progress indicator')),
                ('introduction_text', models.TextField(blank=True, help_text='Introduction text shown before questionnaire starts', null=True)),
                ('completion_message', models.TextField(blank=True, help_text='Message shown upon completion', null=True)),
                ('tags', models.JSONField(blank=True, default=list, help_text='Questionnaire tags for organization')),
                ('usage_count', models.IntegerField(default=0, help_text='Number of times questionnaire has been taken')),
                ('average_completion_time', models.IntegerField(blank=True, help_text='Average completion time in minutes', null=True)),
                ('question_ids', models.JSONField(blank=True, default=list, help_text='Ordered list of question IDs in this questionnaire')),
            ],
            options={
                'ordering': ['-created_at'],
                'db_table': 'questionnaires',
            },
        ),

        # Question model
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('text', models.TextField(help_text='The question text')),
                ('help_text', models.TextField(blank=True, help_text='Help text or additional context for the question', null=True)),
                ('question_type', models.CharField(choices=[('text', 'Text Input'), ('textarea', 'Text Area'), ('single_choice', 'Single Choice (Radio)'), ('multiple_choice', 'Multiple Choice (Checkbox)'), ('select', 'Dropdown Select'), ('rating', 'Rating Scale'), ('yes_no', 'Yes/No'), ('date', 'Date'), ('number', 'Number'), ('email', 'Email'), ('url', 'URL'), ('file_upload', 'File Upload')], default='text', help_text='Type of question input', max_length=20)),
                ('options', models.JSONField(blank=True, default=list, help_text='List of options for choice questions (e.g., [{\'value\': \'yes\', \'label\': \'Yes\', \'score\': 1}])')),
                ('is_required', models.BooleanField(default=False, help_text='Whether this question must be answered')),
                ('validation_rules', models.JSONField(blank=True, default=dict, help_text='Validation rules (e.g., {\'min_length\': 5, \'max_length\': 100, \'pattern\': \'regex\'})')),
                ('enable_scoring', models.BooleanField(default=False, help_text='Whether this question contributes to scoring')),
                ('points', models.IntegerField(default=0, help_text='Points awarded for correct/best answer')),
                ('conditional_logic', models.JSONField(blank=True, default=dict, help_text='Conditional logic rules (e.g., {\'show_if\': {\'question_id\': \'q1\', \'operator\': \'equals\', \'value\': \'yes\'}})')),
                ('depends_on_question_ids', models.JSONField(blank=True, default=list, help_text='List of question IDs this question depends on')),
                ('order', models.IntegerField(default=0, help_text='Display order within questionnaire')),
                ('section', models.CharField(blank=True, help_text='Section or grouping name', max_length=100, null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this question is active/available')),
                ('tags', models.JSONField(blank=True, default=list, help_text='Question tags for organization')),
                ('times_asked', models.IntegerField(default=0, help_text='Number of times this question has been presented')),
                ('skip_rate', models.FloatField(default=0.0, help_text='Percentage of times this question is skipped')),
            ],
            options={
                'ordering': ['order', 'created_at'],
                'db_table': 'questions',
            },
        ),

        # QuestionnaireRun model
        migrations.CreateModel(
            name='QuestionnaireRun',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.UUIDField(blank=True, help_text='User who created this record', null=True)),
                ('updated_by', models.UUIDField(blank=True, help_text='User who last updated this record', null=True)),
                ('questionnaire_id', models.UUIDField(help_text='ID of the questionnaire being taken')),
                ('user_id', models.UUIDField(blank=True, db_index=True, help_text='ID of the user taking the questionnaire (null for anonymous)', null=True)),
                ('status', models.CharField(choices=[('in_progress', 'In Progress'), ('completed', 'Completed'), ('abandoned', 'Abandoned'), ('expired', 'Expired')], default='in_progress', help_text='Current status of the questionnaire run', max_length=20)),
                ('current_question_index', models.IntegerField(default=0, help_text='Index of the current question being answered')),
                ('questions_answered', models.IntegerField(default=0, help_text='Number of questions answered so far')),
                ('total_questions', models.IntegerField(default=0, help_text='Total number of questions in this run (may vary due to conditional logic)')),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now, help_text='When the questionnaire run was started')),
                ('completed_at', models.DateTimeField(blank=True, help_text='When the questionnaire run was completed', null=True)),
                ('time_spent_seconds', models.IntegerField(default=0, help_text='Total time spent on questionnaire in seconds')),
                ('answers', models.JSONField(blank=True, default=dict, help_text='Dictionary of question_id -> answer_value mappings')),
                ('enable_scoring', models.BooleanField(default=False, help_text='Whether this run supports scoring')),
                ('current_score', models.IntegerField(default=0, help_text='Current score accumulated')),
                ('max_possible_score', models.IntegerField(default=0, help_text='Maximum possible score for this run')),
                ('passing_score', models.IntegerField(blank=True, help_text='Minimum passing score (if applicable)', null=True)),
                ('visible_question_ids', models.JSONField(blank=True, default=list, help_text='Ordered list of question IDs visible to the user')),
                ('answered_question_ids', models.JSONField(blank=True, default=list, help_text='List of question IDs that have been answered')),
                ('skipped_question_ids', models.JSONField(blank=True, default=list, help_text='List of question IDs that were skipped')),
                ('conditional_state', models.JSONField(blank=True, default=dict, help_text='Current state for conditional logic evaluation')),
                ('session_token', models.CharField(blank=True, help_text='Token for resuming anonymous sessions', max_length=100, null=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='When this run expires (for time-limited questionnaires)', null=True)),
                ('user_agent', models.TextField(blank=True, help_text='Browser/client user agent', null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, help_text='Client IP address', null=True)),
                ('final_score_percentage', models.FloatField(blank=True, help_text='Final score as percentage', null=True)),
                ('passed', models.BooleanField(blank=True, help_text='Whether the run passed (if scoring enabled)', null=True)),
                ('feedback', models.TextField(blank=True, help_text='User feedback or comments', null=True)),
            ],
            options={
                'ordering': ['-started_at'],
                'db_table': 'questionnaire_runs',
            },
        ),

        # Indexes
        migrations.AddIndex(
            model_name='questionnaire',
            index=models.Index(fields=['status', 'questionnaire_type'], name='questionnaire_status_type_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnaire',
            index=models.Index(fields=['category'], name='questionnaire_category_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnaire',
            index=models.Index(fields=['created_at'], name='questionnaire_created_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnaire',
            index=models.Index(fields=['usage_count'], name='questionnaire_usage_idx'),
        ),

        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['question_type'], name='question_type_idx'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['is_active'], name='question_active_idx'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['order'], name='question_order_idx'),
        ),
        migrations.AddIndex(
            model_name='question',
            index=models.Index(fields=['section'], name='question_section_idx'),
        ),

        migrations.AddIndex(
            model_name='questionnairerun',
            index=models.Index(fields=['questionnaire_id', 'status'], name='run_questionnaire_status_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnairerun',
            index=models.Index(fields=['user_id', 'status'], name='run_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnairerun',
            index=models.Index(fields=['status', 'started_at'], name='run_status_started_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnairerun',
            index=models.Index(fields=['session_token'], name='run_session_token_idx'),
        ),
        migrations.AddIndex(
            model_name='questionnairerun',
            index=models.Index(fields=['expires_at'], name='run_expires_idx'),
        ),
    ]
