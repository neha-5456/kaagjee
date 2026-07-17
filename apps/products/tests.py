from django.test import TestCase
from django.urls import reverse

from apps.categories.models import Category, Subcategory
from apps.products.admin import ProductAdminForm
from apps.products.models import Product


class ProductAdminFormTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Legal', slug='legal')
        self.other_category = Category.objects.create(name='Finance', slug='finance')
        self.subcategory = Subcategory.objects.create(category=self.category, name='PAN Card', slug='pan-card')
        self.other_subcategory = Subcategory.objects.create(category=self.category, name='Aadhaar Card', slug='aadhaar-card')
        self.product = Product.objects.create(
            title='Test Product',
            slug='test-product',
            full_price='100.00',
            half_price='50.00',
            category=self.category,
            subcategory=self.subcategory,
        )
        self.product.categories.set([self.category])
        self.product.subcategories.set([self.subcategory])

    def test_save_syncs_single_category_and_subcategory_from_selected_m2m_values(self):
        form = ProductAdminForm(
            data={
                'title': self.product.title,
                'slug': self.product.slug,
                'short_description': '',
                'description': '',
                'featured_image': '',
                'youtube_link': '',
                'full_price': '120.00',
                'half_price': '60.00',
                'original_price': '',
                'allow_half_payment': True,
                'is_govt_tax_included': '',
                'form_title': 'Application Form',
                'form_description': '',
                'form_schema': '[]',
                'preview_template': '',
                'is_preview_enabled': True,
                'status': Product.Status.ACTIVE,
                'is_featured': False,
                'is_popular': False,
                'meta_title': '',
                'meta_description': '',
                'meta_keywords': '',
                'processing_time': '',
                'documents_required': '',
                'how_its_work': '',
                'data_privacy_policy': '',
                'orders_count': 0,
                'views_count': 0,
                'categories': [self.category.pk, self.other_category.pk],
                'subcategories': [self.other_subcategory.pk],
                'available_states': [],
                'available_cities': [],
            },
            instance=self.product,
        )

        self.assertTrue(form.is_valid(), form.errors)

        saved_product = form.save()

        self.assertIn(saved_product.category_id, [self.category.pk, self.other_category.pk])
        self.assertEqual(saved_product.subcategory_id, self.other_subcategory.pk)
        self.assertEqual(sorted(saved_product.categories.values_list('pk', flat=True)), sorted([self.category.pk, self.other_category.pk]))
        self.assertEqual(list(saved_product.subcategories.values_list('pk', flat=True)), [self.other_subcategory.pk])


class ProductListViewTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Legal', slug='legal')
        self.subcategory = Subcategory.objects.create(category=self.category, name='PAN Card Services', slug='pan-card-services')
        self.other_subcategory = Subcategory.objects.create(category=self.category, name='Aadhaar Services', slug='aadhaar-services')

        self.product_one = Product.objects.create(
            title='Product One',
            slug='product-one',
            full_price='100.00',
            half_price='50.00',
            category=self.category,
            subcategory=self.subcategory,
            status=Product.Status.ACTIVE,
        )
        self.product_one.categories.set([self.category])
        self.product_one.subcategories.set([self.subcategory])

        self.product_two = Product.objects.create(
            title='Product Two',
            slug='product-two',
            full_price='120.00',
            half_price='60.00',
            category=self.category,
            subcategory=self.subcategory,
            status=Product.Status.ACTIVE,
        )
        self.product_two.categories.set([self.category])
        self.product_two.subcategories.set([self.subcategory])

        self.product_three = Product.objects.create(
            title='Product Three',
            slug='product-three',
            full_price='140.00',
            half_price='70.00',
            category=self.category,
            subcategory=self.other_subcategory,
            status=Product.Status.ACTIVE,
        )
        self.product_three.categories.set([self.category])
        self.product_three.subcategories.set([self.other_subcategory])

    def test_products_list_supports_subcategory_slug_filter_and_pagination(self):
        response = self.client.get(reverse('products:product-list'), {'subcategory_slug': self.subcategory.slug, 'page': 1})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        self.assertEqual(payload['count'], 2)
        self.assertEqual(len(payload['data']), 2)
        self.assertEqual(payload['data'][0]['slug'], self.product_two.slug)

    def test_products_by_category_includes_m2m_category_products(self):
        # Product with no direct FK category but M2M category should still appear
        product_four = Product.objects.create(
            title='Product Four',
            slug='product-four',
            full_price='160.00',
            half_price='80.00',
            status=Product.Status.ACTIVE,
        )
        product_four.category = None
        product_four.save()
        product_four.categories.set([self.category])
        product_four.subcategories.set([self.subcategory])

        response = self.client.get(reverse('products:products-by-category', args=[self.category.slug]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['success'])
        products = payload.get('results') or payload.get('data') or []
        self.assertIn('product-four', [item['slug'] for item in products])

    def test_products_by_category_only_shows_category_level_products_by_default(self):
        product_category_level = Product.objects.create(
            title='Product Category Level',
            slug='product-category-level',
            full_price='180.00',
            half_price='90.00',
            category=self.category,
            status=Product.Status.ACTIVE,
        )
        product_category_level.categories.set([self.category])

        product_with_sub = Product.objects.create(
            title='Product With Sub',
            slug='product-with-sub',
            full_price='200.00',
            half_price='100.00',
            category=self.category,
            subcategory=self.subcategory,
            status=Product.Status.ACTIVE,
        )
        product_with_sub.categories.set([self.category])
        product_with_sub.subcategories.set([self.subcategory])

        product_with_fk_sub_only = Product.objects.create(
            title='Product With FK Sub Only',
            slug='product-with-fk-sub-only',
            full_price='220.00',
            half_price='110.00',
            category=self.category,
            subcategory=self.subcategory,
            status=Product.Status.ACTIVE,
        )
        product_with_fk_sub_only.categories.set([self.category])

        response = self.client.get(reverse('products:products-by-category', args=[self.category.slug]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        products = payload.get('results') or payload.get('data') or []
        self.assertEqual(sorted([item['slug'] for item in products]), sorted(['product-category-level', 'product-with-fk-sub-only']))
