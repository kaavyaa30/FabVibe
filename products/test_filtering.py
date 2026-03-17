from django.test import TestCase, Client
from django.urls import reverse
from products.models import Category, Product, ProductSize, ProductColor


class ProductFilteringTestCase(TestCase):
    """Test cases for product filtering functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create products with different attributes
        self.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=self.category,
            description='Test product 1',
            price=50.00,
            brand='Brand A',
            inventory=10
        )
        
        self.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=self.category,
            description='Test product 2',
            price=100.00,
            brand='Brand B',
            inventory=10
        )
        
        self.product3 = Product.objects.create(
            name='Product 3',
            slug='product-3',
            category=self.category,
            description='Test product 3',
            price=150.00,
            brand='Brand A',
            inventory=10
        )
        
        # Add sizes
        ProductSize.objects.create(product=self.product1, size='S', is_available=True)
        ProductSize.objects.create(product=self.product1, size='M', is_available=True)
        ProductSize.objects.create(product=self.product2, size='M', is_available=True)
        ProductSize.objects.create(product=self.product2, size='L', is_available=True)
        ProductSize.objects.create(product=self.product3, size='L', is_available=True)
        ProductSize.objects.create(product=self.product3, size='XL', is_available=True)
        
        # Add colors
        ProductColor.objects.create(product=self.product1, color_name='Red', color_code='#FF0000', is_available=True)
        ProductColor.objects.create(product=self.product2, color_name='Blue', color_code='#0000FF', is_available=True)
        ProductColor.objects.create(product=self.product3, color_name='Red', color_code='#FF0000', is_available=True)
    
    def test_price_range_filter_min(self):
        """Test filtering by minimum price"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'min_price': '75'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product2, products)
        self.assertIn(self.product3, products)
        self.assertNotIn(self.product1, products)
    
    def test_price_range_filter_max(self):
        """Test filtering by maximum price"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'max_price': '100'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product2, products)
        self.assertNotIn(self.product3, products)
    
    def test_price_range_filter_min_max(self):
        """Test filtering by both minimum and maximum price"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'min_price': '75', 'max_price': '125'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertIn(self.product2, products)
    
    def test_size_filter_single(self):
        """Test filtering by a single size"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'size': ['M']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product2, products)
    
    def test_size_filter_multiple(self):
        """Test filtering by multiple sizes"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'size': ['S', 'L']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 3)
    
    def test_color_filter_single(self):
        """Test filtering by a single color"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'color': ['Red']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product3, products)
    
    def test_color_filter_multiple(self):
        """Test filtering by multiple colors"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'color': ['Red', 'Blue']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 3)
    
    def test_brand_filter_single(self):
        """Test filtering by a single brand"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'brand': ['Brand A']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product3, products)
    
    def test_brand_filter_multiple(self):
        """Test filtering by multiple brands"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'brand': ['Brand A', 'Brand B']})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 3)
    
    def test_multiple_filters_combined(self):
        """Test applying multiple filters simultaneously"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'min_price': '50',
            'max_price': '150',
            'size': ['L'],
            'brand': ['Brand A']
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertIn(self.product3, products)
    
    def test_filter_persistence_across_pagination(self):
        """Test that filters persist when navigating between pages"""
        # Create more products to trigger pagination
        for i in range(15):
            Product.objects.create(
                name=f'Extra Product {i}',
                slug=f'extra-product-{i}',
                category=self.category,
                description=f'Extra product {i}',
                price=75.00,
                brand='Brand A',
                inventory=10
            )
        
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'brand': ['Brand A'], 'page': '1'})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('query_string', response.context)
        self.assertIn('brand=Brand+A', response.context['query_string'])
    
    def test_sorting_with_filters(self):
        """Test that sorting works with filters applied"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'brand': ['Brand A'],
            'sort': 'price_low'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 2)
        # Check that products are sorted by price (low to high)
        self.assertEqual(products[0], self.product1)
        self.assertEqual(products[1], self.product3)
    
    def test_available_filter_options(self):
        """Test that available filter options are correctly provided"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Check available sizes
        available_sizes = list(response.context['available_sizes'])
        self.assertIn('S', available_sizes)
        self.assertIn('M', available_sizes)
        self.assertIn('L', available_sizes)
        self.assertIn('XL', available_sizes)
        
        # Check available colors
        available_colors = list(response.context['available_colors'])
        self.assertIn('Red', available_colors)
        self.assertIn('Blue', available_colors)
        
        # Check available brands
        available_brands = list(response.context['available_brands'])
        self.assertIn('Brand A', available_brands)
        self.assertIn('Brand B', available_brands)
    
    def test_selected_filters_in_context(self):
        """Test that selected filters are passed to template context"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'size': ['M', 'L'],
            'color': ['Red'],
            'brand': ['Brand A'],
            'min_price': '50',
            'max_price': '150'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_sizes'], ['M', 'L'])
        self.assertEqual(response.context['selected_colors'], ['Red'])
        self.assertEqual(response.context['selected_brands'], ['Brand A'])
        self.assertEqual(response.context['min_price'], '50')
        self.assertEqual(response.context['max_price'], '150')
    
    def test_invalid_price_values(self):
        """Test that invalid price values are handled gracefully"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'min_price': 'invalid', 'max_price': 'invalid'})
        
        self.assertEqual(response.status_code, 200)
        # Should return all products when invalid prices are provided
        products = list(response.context['products'])
        self.assertEqual(len(products), 3)
    
    def test_no_products_match_filters(self):
        """Test behavior when no products match the applied filters"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'min_price': '1000'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        self.assertEqual(len(products), 0)
