from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("sequences", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sequence",
            name="last",
            field=models.PositiveBigIntegerField(verbose_name="last value"),
        ),
    ]
