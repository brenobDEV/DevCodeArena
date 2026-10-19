# Migration incremental: mantém os perfis e desafios existentes.
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prog", "0002_remove_profile_company_name_remove_profile_role_and_more")]

    operations = [
        migrations.AddField(model_name="challenge", name="start_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="challenge", name="period", field=models.CharField(choices=[("weekly", "Semanal"), ("monthly", "Mensal")], default="weekly", max_length=8)),
        migrations.AddField(model_name="challenge", name="difficulty", field=models.CharField(choices=[("beginner", "Iniciante"), ("intermediate", "Intermediário"), ("advanced", "Avançado")], default="intermediate", max_length=16)),
        migrations.AddField(model_name="challenge", name="languages", field=models.CharField(blank=True, max_length=240)),
        migrations.AddField(model_name="challenge", name="technologies", field=models.CharField(blank=True, max_length=240)),
        migrations.AddField(model_name="challenge", name="requirements", field=models.TextField(blank=True)),
        migrations.AddField(model_name="challenge", name="evaluation_criteria", field=models.TextField(blank=True)),
        # Existing challenges are marked published during this data-preserving migration.
        migrations.AddField(model_name="challenge", name="status", field=models.CharField(choices=[("draft", "Rascunho"), ("published", "Publicado"), ("closed", "Encerrado")], default="published", max_length=10)),
        migrations.AlterField(model_name="challenge", name="status", field=models.CharField(choices=[("draft", "Rascunho"), ("published", "Publicado"), ("closed", "Encerrado")], default="draft", max_length=10)),
        migrations.AlterField(model_name="challenge", name="reward", field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=10)),
        migrations.AlterField(model_name="challenge", name="is_active", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="challenge", name="updated_at", field=models.DateTimeField(default=django.utils.timezone.now), preserve_default=False),
        migrations.AlterField(model_name="challenge", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.CreateModel(
            name="Participation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("registered", "Inscrito"), ("selected", "Selecionado"), ("not_selected", "Não selecionado")], default="registered", max_length=16)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("challenge", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="prog.challenge")),
                ("developer", models.ForeignKey(limit_choices_to={"tipo": "developer"}, on_delete=django.db.models.deletion.CASCADE, related_name="participations", to="prog.profile")),
            ],
            options={"ordering": ["-joined_at"]},
        ),
        migrations.AddConstraint(model_name="participation", constraint=models.UniqueConstraint(fields=("challenge", "developer"), name="unique_challenge_developer")),
        migrations.AddIndex(model_name="participation", index=models.Index(fields=["challenge", "status"], name="participation_ch_status_idx")),
        migrations.AddIndex(model_name="participation", index=models.Index(fields=["developer", "status"], name="participation_dev_status_idx")),
        migrations.CreateModel(
            name="Submission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("repository_url", models.URLField(max_length=500)),
                ("demo_url", models.URLField(blank=True, max_length=500)),
                ("notes", models.TextField(blank=True)),
                ("score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("feedback", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("participation", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="submission", to="prog.participation")),
            ],
            options={"ordering": ["-submitted_at"]},
        ),
        migrations.AddIndex(model_name="submission", index=models.Index(fields=["score", "submitted_at"], name="submission_score_date_idx")),
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("challenge", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conversations", to="prog.challenge")),
                ("company", models.ForeignKey(limit_choices_to={"tipo": "company"}, on_delete=django.db.models.deletion.CASCADE, related_name="company_conversations", to="prog.profile")),
                ("developer", models.ForeignKey(limit_choices_to={"tipo": "developer"}, on_delete=django.db.models.deletion.CASCADE, related_name="developer_conversations", to="prog.profile")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.AddConstraint(model_name="conversation", constraint=models.UniqueConstraint(fields=("company", "developer", "challenge"), name="unique_company_developer_challenge_chat")),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField(max_length=4000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="prog.conversation")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_messages", to="prog.profile")),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(model_name="message", index=models.Index(fields=["conversation", "created_at"], name="message_conversation_date_idx")),
        migrations.AddIndex(model_name="message", index=models.Index(fields=["conversation", "read_at"], name="message_conversation_read_idx")),
        migrations.AddIndex(model_name="challenge", index=models.Index(fields=["status", "period", "deadline"], name="challenge_listing_idx")),
        migrations.AddIndex(model_name="challenge", index=models.Index(fields=["company", "status"], name="challenge_company_status_idx")),
    ]
