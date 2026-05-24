"""
Kaagjee - Product Price Calculator
===================================
Calculates total product price based on:
1. Base product price (full_price)
2. Selected dropdown/radio options that have price values (has_price=True)

Usage in orders/views.py:
    from apps.products.utils import calculate_total_price
    
    result = calculate_total_price(product, form_data)
    # result['total_price'] = base + options
"""
from decimal import Decimal


def calculate_total_price(product, form_data):
    base_price = Decimal(str(product.full_price))
    options_price = Decimal('0')
    price_breakdown = []

    if not product.form_schema or not isinstance(product.form_schema, list):
        return {
            'base_price': float(base_price),
            'options_price': 0,
            'total_price': float(base_price),
            'price_breakdown': []
        }

    def process_fields(fields):
        nonlocal options_price
        for field in (fields or []):
            field_name = field.get('name', '')
            field_type = field.get('field_type', '')
            has_price  = field.get('has_price', False)

            if has_price and field_type in ('dropdown', 'radio', 'checkbox'):
                selected_value = form_data.get(field_name, '')
                if not selected_value:
                    # recurse into all options' nested_fields even if nothing selected
                    for option in field.get('options', []):
                        process_fields(option.get('nested_fields') or [])
                    continue

                # checkbox can be a list of selected values
                selected_list = selected_value if isinstance(selected_value, list) else [selected_value]

                for option in field.get('options', []):
                    opt_value = option.get('value', '')
                    opt_label = option.get('label', '')
                    if opt_value in selected_list or opt_label in selected_list:
                        option_price = Decimal(str(option.get('price', 0)))
                        if option_price > 0:
                            options_price += option_price
                            price_breakdown.append({
                                'field_name': field_name,
                                'field_label': field.get('label', ''),
                                'option_label': opt_label,
                                'option_value': opt_value,
                                'price': float(option_price)
                            })
                        # recurse into nested_fields of every selected option
                        process_fields(option.get('nested_fields') or [])
            else:
                # non-priced field — still recurse into nested_fields of its options
                for option in field.get('options', []):
                    process_fields(option.get('nested_fields') or [])

    process_fields(product.form_schema)

    total_price = base_price + options_price

    return {
        'base_price': float(base_price),
        'options_price': float(options_price),
        'total_price': float(total_price),
        'price_breakdown': price_breakdown
    }


def get_priced_fields_from_schema(form_schema):
    """
    Extract fields with pricing info from form schema.
    Frontend uses this to show dynamic prices in dropdown options.
    Returns list of fields that have has_price=True (including nested).
    """
    priced_fields = []

    def collect(fields):
        for field in (fields or []):
            if field.get('has_price', False) and field.get('field_type') in ('dropdown', 'radio', 'checkbox'):
                priced_fields.append({
                    'id': field.get('id', ''),
                    'label': field.get('label', ''),
                    'name': field.get('name', ''),
                    'field_type': field.get('field_type', ''),
                    'options': [
                        {
                            'label': opt.get('label', ''),
                            'value': opt.get('value', ''),
                            'price': opt.get('price', 0)
                        }
                        for opt in field.get('options', [])
                    ]
                })
            for opt in field.get('options', []):
                collect(opt.get('nested_fields') or [])

    if form_schema and isinstance(form_schema, list):
        collect(form_schema)

    return priced_fields