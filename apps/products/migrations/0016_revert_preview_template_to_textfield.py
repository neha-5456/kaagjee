from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0015_convert_preview_template_to_pages'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='preview_template',
            field=models.TextField(
                blank=True,
                verbose_name='Preview Pages (HTML)',
                help_text='Multiple pages supported. Use {{field_name}} placeholders.',
            ),
        ),
    ]
