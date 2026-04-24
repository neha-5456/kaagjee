from django.db import migrations, models
import json


def migrate_template_to_pages(apps, schema_editor):
    """Convert existing preview_template text to pages JSON array."""
    Product = apps.get_model('products', 'Product')
    for product in Product.objects.all():
        old = product.preview_template
        if old and isinstance(old, str) and old.strip():
            product.preview_template = [{"title": "Page 1", "template": old}]
        else:
            product.preview_template = []
        product.save(update_fields=['preview_template'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0014_product_preview_pages'),
    ]

    operations = [
        # Step 1: Remove preview_pages field
        migrations.RemoveField(
            model_name='product',
            name='preview_pages',
        ),
        # Step 2: Change preview_template from TextField to JSONField
        migrations.AlterField(
            model_name='product',
            name='preview_template',
            field=models.JSONField(
                blank=True,
                default=list,
                verbose_name='Preview Pages',
                help_text='Multiple pages — each page has a title and HTML template with {{placeholders}}',
            ),
        ),
        # Step 3: Migrate existing text data to pages format
        migrations.RunPython(migrate_template_to_pages, migrations.RunPython.noop),
    ]
