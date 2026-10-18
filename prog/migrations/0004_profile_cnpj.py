from django.db import migrations, models

from prog.migration_operations import SharedAddField, SharedAlterField


class Migration(migrations.Migration):
    dependencies = [("prog", "0003_platform_features")]

    operations = [
        SharedAddField(
            model_name="profile", name="cnpj",
            field=models.CharField(blank=True, max_length=14, null=True, unique=True),
            peer_migration="0005_profile_cnpj_alter_profile_cpf",
        ),
        SharedAlterField(
            model_name="profile", name="cpf",
            field=models.CharField(blank=True, max_length=11, null=True, unique=True),
            peer_migration="0005_profile_cnpj_alter_profile_cpf",
        ),
    ]