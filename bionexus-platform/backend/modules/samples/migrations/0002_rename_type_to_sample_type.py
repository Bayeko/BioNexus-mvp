from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("samples", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sample",
            old_name="type",
            new_name="sample_type",
        ),
    ]
