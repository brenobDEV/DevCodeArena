from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("prog", "0003_platform_features")]

    operations = [
        migrations.AddField(
            model_name="profile", name="cnpj",
            field=models.CharField(blank=True, max_length=14, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="profile", name="cpf",
            field=models.CharField(blank=True, max_length=11, null=True, unique=True),
        ),
    ]