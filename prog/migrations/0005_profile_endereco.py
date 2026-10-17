from django.db import migrations, models

from prog.migration_operations import SharedAddField


class Migration(migrations.Migration):
    dependencies = [("prog", "0004_profile_cnpj")]

    operations = [
        SharedAddField(model_name="profile", name="cep", field=models.CharField(blank=True, max_length=8), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="logradouro", field=models.CharField(blank=True, max_length=150), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="numero", field=models.CharField(blank=True, max_length=10), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="complemento", field=models.CharField(blank=True, max_length=80), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="bairro", field=models.CharField(blank=True, max_length=80), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="cidade", field=models.CharField(blank=True, max_length=80), peer_migration="0006_profile_endereco"),
        SharedAddField(model_name="profile", name="uf", field=models.CharField(blank=True, max_length=2), peer_migration="0006_profile_endereco"),
    ]