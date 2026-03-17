from django.test import TestCase, Client
from django.urls import reverse
from .models import Category, Product


class SearchProductsViewTest(TestCase):
    """Test product search functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(
            name='Clothing',
            slug='clothing',
            is_active=True
        )
        
        # Create test products with various names and descriptions
        self.product1 = Product.objects.create(
            name='Blue Cotton Shirt',
            slug='blue-cotton-shirt',
            category=self.category,
            description='A comfortable blue cotton shirt for casual wear',
            price=29.99,
            inventory=10,
            is_active=True
        )
        
        self.product2 = Product.objects.create(
            name='Red Silk Dress',
            slug='red-silk-dress',
            category=self.category,
            description='Elegant red silk dress perfect for evening events',
            price=89.99,
            inventory=5,
            is_active=True
        )
        
        self.product3 = Product.objects.create(
            name='Black Leather Jacket',
            slug='black-leather-jacket',
            category=self.category,
            description='Stylish black leather jacket with cotton lining',
            price=149.99,
            inventory=3,
            is_active=True
        )
        
        self.product4 = Product.objects.create(
            name='White Cotton Pants',
            slug='white-cotton-pants',
            category=self.category,
            description='Comfortable white cotton pants for summer',
            price=39.99,
            inventory=15,
            is_active=True
        )
        
        # Create inactive product (should not appear in search)
        self.inactive_product = Product.objects.create(
            name='Gray Wool Sweater',
            slug='gray-wool-sweater',
            category=self.category,
            description='Warm gray wool sweater',
            price=59.99,
            inventory=8,
            is_active=False
        )
    
    def test_search_by_product_name(self):
        """Test searching products by name"""
        response = self.client.get(reverse('products:search'), {'q': 'shirt'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/search_results.html')
        
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Blue Cotton Shirt')
    
    def test_search_by_product_description(self):
        """Test searching products by description"""
        response = self.client.get(reverse('products:search'), {'q': 'elegant'})
        self.assertEqual(response.status_code, 200)
        
        products = list(response.context['products'])
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].name, 'Red Silk Dress')
    
    def test_search_matches_multiple_products(self):
        """Test search query matching multiple products"""
        response = self.client.get(reverse('products:search'), {'q': 'cotton'})
        self.assertEqual(response.status_code, 200)
        
        products = list(response.context['products'])
        # Should match: Blue Cotton Shirt, Black Leather Jacket (cotton lining), White Cotton Pants
        self.assertEqual(len(products), 3)
        
        product_names = [p.name for p in products]
        self.assertIn('Blue Cotton Shirt', product_names)
        self.assertIn('Black Leather Jacket', product_names)
        self.assertIn('White Cotton Pants', product_names)
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive"""
        # Test uppercase
        response1 = self.client.get(reverse('products:search'), {'q': 'COTTON'})
        products1 = list(response1.context['products'])
        
        # Test lowercase
        response2 = self.client.get(reverse('products:search'), {'q': 'cotton'})
        products2 = list(response2.context['products'])
        
        # Test mixed case
        response3 = self.client.get(reverse('products:search'), {'q': 'CoTtOn'})
        products3 = list(response3.context['products'])
        
        # All should return same results
        self.assertEqual(len(products1), len(products2))
        self.assertEqual(len(products2), len(products3))
        self.assertEqual(len(products1), 3)
    
    def test_search_empty_query(self):
        """Test search with empty query returns no results"""
        response = self.client.get(reverse('products:search'), {'q': ''})
        self.assertEqual(response.status_code, 200)
        
        products = list(response.context['products'])
        self.assertEqual(len(products), 0)
        self.assertEqual(response.context['total_results'], 0)
    
    def test_search_no_matches(self):
        """Test search with no matching products"""
        response = self.client.get(reverse('products:search'), {'q': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        
        products = list(response.context['products'])
        self.assertEqual(len(products), 0)
        self.assertEqual(response.context['total_results'], 0)
    
    def test_search_excludes_inactive_products(self):
        """Test that search excludes inactive products"""
        response = self.client.get(reverse('products:search'), {'q': 'wool'})
        self.assertEqual(response.status_code, 200)
        
        products = list(response.context['products'])
        # Should not find the inactive Gray Wool Sweater
        self.assertEqual(len(products), 0)
    
    def test_search_results_ordered_by_newest(self):
        """Test that search results are ordered by creation date (newest first)"""
        response = self.client.get(reverse('products:search'), {'q': 'cotton'})
        products = list(response.context['products'])
        
        # Check that products are ordered by newest first
        for i in range(len(products) - 1):
            self.assertGreaterEqual(
                products[i].created_at,
                products[i + 1].created_at
            )
    
    def test_search_context_data(self):
        """Test that search view provides correct context data"""
        query = 'cotton'
        response = self.client.get(reverse('products:search'), {'q': query})
        self.assertEqual(response.status_code, 200)
        
        # Check context variables
        self.assertIn('query', response.context)
        self.assertEqual(response.context['query'], query)
        
        self.assertIn('products', response.context)
        self.assertIn('page_obj', response.context)
        self.assertIn('total_results', response.context)
        self.assertEqual(response.context['total_results'], 3)
    
    def test_search_pagination(self):
        """Test that search results are paginated"""
        # Create 15 products with 'test' in name
        for i in range(15):
            Product.objects.create(
                name=f'Test Product {i+1}',
                slug=f'test-product-{i+1}',
                category=self.category,
                description=f'Description for test product {i+1}',
                price=29.99 + i,
                inventory=10,
                is_active=True
            )
        
        # First page should have 12 products
        response = self.client.get(reverse('products:search'), {'q': 'test'})
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        self.assertEqual(len(products), 12)
        
        # Second page should have remaining 3 products
        response = self.client.get(reverse('products:search'), {'q': 'test', 'page': 2})
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        self.assertEqual(len(products), 3)
    
    def test_search_whitespace_handling(self):
        """Test that search handles leading/trailing whitespace"""
        response1 = self.client.get(reverse('products:search'), {'q': '  cotton  '})
        response2 = self.client.get(reverse('products:search'), {'q': 'cotton'})
        
        products1 = list(response1.context['products'])
        products2 = list(response2.context['products'])
        
        # Should return same results
        self.assertEqual(len(products1), len(products2))


class SearchSuggestionsViewTest(TestCase):
    """Test AJAX search auto-suggestions"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test category
        self.category = Category.objects.create(
            name='Clothing',
            slug='clothing',
            is_active=True
        )
        
        # Create test products
        self.products = []
        product_names = [
            'Blue Cotton Shirt',
            'Blue Denim Jeans',
            'Blue Silk Tie',
            'Red Cotton Dress',
            'Black Leather Jacket',
            'White Cotton Pants',
            'Green Wool Sweater',
            'Yellow Summer Dress',
            'Purple Evening Gown',
            'Orange Casual Shirt',
            'Pink Floral Blouse',
            'Brown Leather Boots'
        ]
        
        for i, name in enumerate(product_names):
            product = Product.objects.create(
                name=name,
                slug=name.lower().replace(' ', '-'),
                category=self.category,
                description=f'Description for {name}',
                price=29.99 + i * 10,
                inventory=10,
                is_active=True
            )
            self.products.append(product)
        
        # Create inactive product (should not appear in suggestions)
        self.inactive_product = Product.objects.create(
            name='Blue Inactive Product',
            slug='blue-inactive-product',
            category=self.category,
            description='This is inactive',
            price=99.99,
            inventory=5,
            is_active=False
        )
    
    def test_suggestions_endpoint_returns_json(self):
        """Test that suggestions endpoint returns JSON response"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'blue'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
    
    def test_suggestions_match_product_names(self):
        """Test that suggestions match product names"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'blue'})
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('suggestions', data)
        suggestions = data['suggestions']
        
        # Should return 3 products with 'blue' in name
        self.assertEqual(len(suggestions), 3)
        
        suggestion_names = [s['name'] for s in suggestions]
        self.assertIn('Blue Cotton Shirt', suggestion_names)
        self.assertIn('Blue Denim Jeans', suggestion_names)
        self.assertIn('Blue Silk Tie', suggestion_names)
    
    def test_suggestions_limited_to_10_results(self):
        """Test that suggestions are limited to 10 results"""
        # Create 15 products with 'test' in name
        for i in range(15):
            Product.objects.create(
                name=f'Test Product {i+1}',
                slug=f'test-product-{i+1}',
                category=self.category,
                description=f'Description {i+1}',
                price=29.99,
                inventory=10,
                is_active=True
            )
        
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'test'})
        data = response.json()
        suggestions = data['suggestions']
        
        # Should return maximum 10 suggestions
        self.assertEqual(len(suggestions), 10)
    
    def test_suggestions_require_minimum_2_characters(self):
        """Test that suggestions require at least 2 characters"""
        # Single character query
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'b'})
        data = response.json()
        suggestions = data['suggestions']
        
        # Should return empty list
        self.assertEqual(len(suggestions), 0)
        
        # Two character query
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'bl'})
        data = response.json()
        suggestions = data['suggestions']
        
        # Should return results
        self.assertGreater(len(suggestions), 0)
    
    def test_suggestions_empty_query(self):
        """Test suggestions with empty query"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': ''})
        data = response.json()
        suggestions = data['suggestions']
        
        self.assertEqual(len(suggestions), 0)
    
    def test_suggestions_case_insensitive(self):
        """Test that suggestions are case-insensitive"""
        response1 = self.client.get(reverse('products:search_suggestions'), {'q': 'BLUE'})
        response2 = self.client.get(reverse('products:search_suggestions'), {'q': 'blue'})
        response3 = self.client.get(reverse('products:search_suggestions'), {'q': 'BlUe'})
        
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()
        
        # All should return same number of results
        self.assertEqual(len(data1['suggestions']), len(data2['suggestions']))
        self.assertEqual(len(data2['suggestions']), len(data3['suggestions']))
    
    def test_suggestions_exclude_inactive_products(self):
        """Test that suggestions exclude inactive products"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'blue'})
        data = response.json()
        suggestions = data['suggestions']
        
        # Should not include 'Blue Inactive Product'
        suggestion_names = [s['name'] for s in suggestions]
        self.assertNotIn('Blue Inactive Product', suggestion_names)
        self.assertEqual(len(suggestions), 3)  # Only active blue products
    
    def test_suggestions_include_product_data(self):
        """Test that suggestions include necessary product data"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'blue'})
        data = response.json()
        suggestions = data['suggestions']
        
        # Check that each suggestion has required fields
        for suggestion in suggestions:
            self.assertIn('id', suggestion)
            self.assertIn('name', suggestion)
            self.assertIn('slug', suggestion)
    
    def test_suggestions_no_matches(self):
        """Test suggestions with no matching products"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': 'nonexistent'})
        data = response.json()
        suggestions = data['suggestions']
        
        self.assertEqual(len(suggestions), 0)
    
    def test_suggestions_whitespace_handling(self):
        """Test that suggestions handle whitespace correctly"""
        response = self.client.get(reverse('products:search_suggestions'), {'q': '  blue  '})
        data = response.json()
        suggestions = data['suggestions']
        
        # Should still return results
        self.assertEqual(len(suggestions), 3)
