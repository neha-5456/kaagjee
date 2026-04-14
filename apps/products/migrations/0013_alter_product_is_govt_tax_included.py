from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0012_product_is_govt_tax_included'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='is_govt_tax_included',
            field=models.CharField(
                blank=True,
                default='',
                help_text='e.g. Govt. Tax Included, All Fees Included, GST Included etc. Leave blank to hide.',
                max_length=200,
                verbose_name='Tax/Fee Label',
            ),
        ),
    ]
