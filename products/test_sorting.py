from django.test import TestCase, Client
from django.urls import reverse
from products.models import Category, Product, ProductSize, ProductColor
from datetime import datetime, timedelta
from django.utils import timezone


class ProductSortingTestCase(TestCase):
    """Test cases for product sorting functionality
    
    **Validates: Requirements 9.1, 9.2, 9.3, 9.4**
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create category
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        # Create products with different prices and dates
        # Product 1: Oldest, medium price
        self.product1 = Product.objects.create(
            name='Product 1',
            slug='product-1',
            category=self.category,
            description='Test product 1',
            price=75.00,
            brand='Brand A',
            inventory=10
        )
        # Manually set created_at to make it oldest
        Product.objects.filter(pk=self.product1.pk).update(
            created_at=timezone.now() - timedelta(days=10)
        )
        self.product1.refresh_from_db()
        
        # Product 2: Middle age, highest price
        self.product2 = Product.objects.create(
            name='Product 2',
            slug='product-2',
            category=self.category,
            description='Test product 2',
            price=150.00,
            brand='Brand B',
            inventory=10
        )
        Product.objects.filter(pk=self.product2.pk).update(
            created_at=timezone.now() - timedelta(days=5)
        )
        self.product2.refresh_from_db()
        
        # Product 3: Newest, lowest price
        self.product3 = Product.objects.create(
            name='Product 3',
            slug='product-3',
            category=self.category,
            description='Test product 3',
            price=50.00,
            brand='Brand A',
            inventory=10
        )
        # This will have the most recent created_at
        
        # Add sizes to products for filter testing
        ProductSize.objects.create(product=self.product1, size='M', is_available=True)
        ProductSize.objects.create(product=self.product2, size='M', is_available=True)
        ProductSize.objects.create(product=self.product3, size='M', is_available=True)
        
        # Add colors to products for filter testing
        ProductColor.objects.create(product=self.product1, color_name='Red', color_code='#FF0000', is_available=True)
        ProductColor.objects.create(product=self.product2, color_name='Blue', color_code='#0000FF', is_available=True)
        ProductColor.objects.create(product=self.product3, color_name='Red', color_code='#FF0000', is_available=True)
    
    def test_sort_by_price_low_to_high(self):
        """Test sorting products by price in ascending order
        
        **Validates: Requirement 9.1**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'price_low'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should have all 3 products
        self.assertEqual(len(products), 3)
        
        # Check order: product3 ($50), product1 ($75), product2 ($150)
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product1)
        self.assertEqual(products[2], self.product2)
        
        # Verify prices are in ascending order
        self.assertLessEqual(products[0].price, products[1].price)
        self.assertLessEqual(products[1].price, products[2].price)
    
    def test_sort_by_price_high_to_low(self):
        """Test sorting products by price in descending order
        
        **Validates: Requirement 9.2**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'price_high'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should have all 3 products
        self.assertEqual(len(products), 3)
        
        # Check order: product2 ($150), product1 ($75), product3 ($50)
        self.assertEqual(products[0], self.product2)
        self.assertEqual(products[1], self.product1)
        self.assertEqual(products[2], self.product3)
        
        # Verify prices are in descending order
        self.assertGreaterEqual(products[0].price, products[1].price)
        self.assertGreaterEqual(products[1].price, products[2].price)
    
    def test_sort_by_newest_first(self):
        """Test sorting products by creation date (newest first)
        
        **Validates: Requirement 9.3**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'newest'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should have all 3 products
        self.assertEqual(len(products), 3)
        
        # Check order: product3 (newest), product2 (middle), product1 (oldest)
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product2)
        self.assertEqual(products[2], self.product1)
        
        # Verify dates are in descending order (newest first)
        self.assertGreaterEqual(products[0].created_at, products[1].created_at)
        self.assertGreaterEqual(products[1].created_at, products[2].created_at)
    
    def test_default_sorting_is_newest_first(self):
        """Test that default sorting (no sort parameter) is newest first"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should default to newest first
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product2)
        self.assertEqual(products[2], self.product1)
    
    def test_sorting_maintains_price_filter(self):
        """Test that price filters are maintained when sorting changes
        
        **Validates: Requirement 9.4**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'min_price': '60',
            'max_price': '160',
            'sort': 'price_low'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should only include product1 ($75) and product2 ($150)
        # product3 ($50) is below min_price
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product2, products)
        self.assertNotIn(self.product3, products)
        
        # Check they're sorted by price (low to high)
        self.assertEqual(products[0], self.product1)
        self.assertEqual(products[1], self.product2)
        
        # Verify filter values are in context
        self.assertEqual(response.context['min_price'], '60')
        self.assertEqual(response.context['max_price'], '160')
    
    def test_sorting_maintains_size_filter(self):
        """Test that size filters are maintained when sorting changes
        
        **Validates: Requirement 9.4**
        """
        # Add different sizes to products
        ProductSize.objects.create(product=self.product1, size='L', is_available=True)
        ProductSize.objects.create(product=self.product2, size='S', is_available=True)
        
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'size': ['M'],
            'sort': 'price_high'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # All products have size M, so all should be included
        self.assertEqual(len(products), 3)
        
        # Check they're sorted by price (high to low)
        self.assertEqual(products[0], self.product2)
        self.assertEqual(products[1], self.product1)
        self.assertEqual(products[2], self.product3)
        
        # Verify filter is maintained
        self.assertEqual(response.context['selected_sizes'], ['M'])
    
    def test_sorting_maintains_color_filter(self):
        """Test that color filters are maintained when sorting changes
        
        **Validates: Requirement 9.4**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'color': ['Red'],
            'sort': 'price_low'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Only product1 and product3 have Red color
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product3, products)
        self.assertNotIn(self.product2, products)
        
        # Check they're sorted by price (low to high)
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product1)
        
        # Verify filter is maintained
        self.assertEqual(response.context['selected_colors'], ['Red'])
    
    def test_sorting_maintains_brand_filter(self):
        """Test that brand filters are maintained when sorting changes
        
        **Validates: Requirement 9.4**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'brand': ['Brand A'],
            'sort': 'newest'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Only product1 and product3 are Brand A
        self.assertEqual(len(products), 2)
        self.assertIn(self.product1, products)
        self.assertIn(self.product3, products)
        self.assertNotIn(self.product2, products)
        
        # Check they're sorted by date (newest first)
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product1)
        
        # Verify filter is maintained
        self.assertEqual(response.context['selected_brands'], ['Brand A'])
    
    def test_sorting_maintains_multiple_filters(self):
        """Test that multiple filters are maintained when sorting changes
        
        **Validates: Requirement 9.4**
        """
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {
            'min_price': '50',
            'max_price': '100',
            'size': ['M'],
            'color': ['Red'],
            'brand': ['Brand A'],
            'sort': 'price_high'
        })
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Only product1 and product3 match all filters
        # product2 is Brand B and Blue
        self.assertEqual(len(products), 2)
        
        # Check they're sorted by price (high to low)
        self.assertEqual(products[0], self.product1)  # $75
        self.assertEqual(products[1], self.product3)  # $50
        
        # Verify all filters are maintained
        self.assertEqual(response.context['min_price'], '50')
        self.assertEqual(response.context['max_price'], '100')
        self.assertEqual(response.context['selected_sizes'], ['M'])
        self.assertEqual(response.context['selected_colors'], ['Red'])
        self.assertEqual(response.context['selected_brands'], ['Brand A'])
        self.assertEqual(response.context['sort_by'], 'price_high')
    
    def test_sort_parameter_in_context(self):
        """Test that sort parameter is passed to template context"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'price_low'})
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_by'], 'price_low')
    
    def test_invalid_sort_parameter_defaults_to_newest(self):
        """Test that invalid sort parameter defaults to newest first"""
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'invalid_sort'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should default to newest first
        self.assertEqual(products[0], self.product3)
        self.assertEqual(products[1], self.product2)
        self.assertEqual(products[2], self.product1)
    
    def test_sorting_with_pagination(self):
        """Test that sorting works correctly with pagination"""
        # Create more products to trigger pagination (12 per page)
        for i in range(12):
            product = Product.objects.create(
                name=f'Extra Product {i}',
                slug=f'extra-product-{i}',
                category=self.category,
                description=f'Extra product {i}',
                price=100.00 + i,
                brand='Brand C',
                inventory=10
            )
            Product.objects.filter(pk=product.pk).update(
                created_at=timezone.now() - timedelta(days=i+1)
            )
        
        url = reverse('products:category_products', args=[self.category.slug])
        response = self.client.get(url, {'sort': 'price_low', 'page': '1'})
        
        self.assertEqual(response.status_code, 200)
        products = list(response.context['products'])
        
        # Should have 12 products on first page
        self.assertEqual(len(products), 12)
        
        # First product should be the cheapest
        self.assertEqual(products[0], self.product3)  # $50
        
        # Verify prices are in ascending order
        for i in range(len(products) - 1):
            self.assertLessEqual(products[i].price, products[i + 1].price)
