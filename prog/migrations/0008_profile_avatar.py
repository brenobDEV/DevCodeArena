from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("prog", "0007_merge_profile_histories"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="avatar",
            field=models.ImageField(blank=True, upload_to="profile_photos/"),
        ),
    ]
