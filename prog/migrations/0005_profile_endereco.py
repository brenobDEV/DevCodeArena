from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prog", "0004_profile_cnpj")]

    operations = [
        migrations.AddField(model_name="profile", name="cep", field=models.CharField(blank=True, max_length=8)),
        migrations.AddField(model_name="profile", name="logradouro", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="profile", name="numero", field=models.CharField(blank=True, max_length=10)),
        migrations.AddField(model_name="profile", name="complemento", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="profile", name="bairro", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="profile", name="cidade", field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name="profile", name="uf", field=models.CharField(blank=True, max_length=2)),
    ]