from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_alter_product_is_govt_tax_included'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='preview_pages',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Multiple pages support — each page has a title and HTML template with {{placeholders}}',
                verbose_name='Preview Pages',
            ),
        ),
    ]
