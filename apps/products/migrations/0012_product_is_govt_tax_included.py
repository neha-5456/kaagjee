from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0011_product_is_preview_enabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_govt_tax_included',
            field=models.BooleanField(default=False, help_text='Check karne par price ke paas "Govt. Tax Included" text dikhega', verbose_name='Govt Tax Included'),
        ),
    ]
