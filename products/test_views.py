from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Banner, Category, Product, ProductImage

User = get_user_model()


class HomeViewTest(TestCase):
    """Test homepage view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test categories
        self.category1 = Category.objects.create(
            name='Men',
            slug='men',
            description='Men clothing',
            is_active=True
        )
        
        self.category2 = Category.objects.create(
            name='Women',
            slug='women',
            description='Women clothing',
            is_active=True
        )
        
        # Create test products
        for i in range(15):
            Product.objects.create(
                name=f'Product {i+1}',
                slug=f'product-{i+1}',
                category=self.category1 if i % 2 == 0 else self.category2,
                description=f'Description for product {i+1}',
                price=29.99 + i,
                inventory=10,
                is_active=True
            )
    
    def test_homepage_loads(self):
        """Test that homepage loads successfully"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/home.html')
    
    def test_homepage_displays_new_arrivals(self):
        """Test that homepage displays 12 newest products"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('new_arrivals', response.context)
        # Should display 12 products even though we created 15
        self.assertEqual(len(response.context['new_arrivals']), 12)
    
    def test_homepage_displays_featured_categories(self):
        """Test that homepage displays featured categories"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('featured_categories', response.context)
    
    def test_homepage_displays_active_banners(self):
        """Test that homepage displays only active banners"""
        # Create active banner
        active_banner = Banner.objects.create(
            title='Summer Sale',
            link_url='https://example.com/sale',
            display_order=1,
            is_active=True
        )
        
        # Create inactive banner
        inactive_banner = Banner.objects.create(
            title='Winter Sale',
            link_url='https://example.com/winter',
            display_order=2,
            is_active=False
        )
        
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('banners', response.context)
        
        # Should only include active banner
        banners = response.context['banners']
        self.assertEqual(len(banners), 1)
        self.assertEqual(banners[0].title, 'Summer Sale')
    
    def test_banner_click_navigation(self):
        """Test that banners have clickable links"""
        banner = Banner.objects.create(
            title='Test Banner',
            link_url='https://example.com/test',
            display_order=1,
            is_active=True
        )
        
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, banner.link_url)
    
    def test_new_arrivals_ordered_by_newest(self):
        """Test that new arrivals are ordered by creation date (newest first)"""
        response = self.client.get(reverse('products:home'))
        new_arrivals = response.context['new_arrivals']
        
        # Check that products are ordered by newest first
        for i in range(len(new_arrivals) - 1):
            self.assertGreaterEqual(
                new_arrivals[i].created_at,
                new_arrivals[i + 1].created_at
            )
    
    def test_only_active_products_displayed(self):
        """Test that only active products are displayed"""
        # Create inactive product
        Product.objects.create(
            name='Inactive Product',
            slug='inactive-product',
            category=self.category1,
            description='This product is inactive',
            price=99.99,
            inventory=5,
            is_active=False
        )
        
        response = self.client.get(reverse('products:home'))
        new_arrivals = response.context['new_arrivals']
        
        # Verify no inactive products in new arrivals
        for product in new_arrivals:
            self.assertTrue(product.is_active)



class CategoryProductsViewTest(TestCase):
    """Test category products listing view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create parent category
        self.parent_category = Category.objects.create(
            name='Men',
            slug='men',
            description='Men clothing',
            is_active=True
        )
        
        # Create subcategories
        self.subcategory1 = Category.objects.create(
            name='Shirts',
            slug='shirts',
            description='Men shirts',
            parent=self.parent_category,
            is_active=True
        )
        
        self.subcategory2 = Category.objects.create(
            name='Pants',
            slug='pants',
            description='Men pants',
            parent=self.parent_category,
            is_active=True
        )
        
        # Create products in parent category
        for i in range(3):
            Product.objects.create(
                name=f'Parent Product {i+1}',
                slug=f'parent-product-{i+1}',
                category=self.parent_category,
                description=f'Product in parent category {i+1}',
                price=29.99 + i,
                inventory=10,
                is_active=True
            )
        
        # Create products in subcategory 1
        for i in range(5):
            Product.objects.create(
                name=f'Shirt {i+1}',
                slug=f'shirt-{i+1}',
                category=self.subcategory1,
                description=f'Shirt product {i+1}',
                price=39.99 + i,
                inventory=10,
                is_active=True
            )
        
        # Create products in subcategory 2
        for i in range(4):
            Product.objects.create(
                name=f'Pants {i+1}',
                slug=f'pants-{i+1}',
                category=self.subcategory2,
                description=f'Pants product {i+1}',
                price=49.99 + i,
                inventory=10,
                is_active=True
            )
    
    def test_parent_category_displays_all_products(self):
        """Test that parent category displays products from category and all subcategories"""
        response = self.client.get(reverse('products:category_products', args=['men']))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/category_products.html')
        
        # Should display 3 (parent) + 5 (shirts) + 4 (pants) = 12 products
        products = response.context['products']
        self.assertEqual(len(products), 12)
    
    def test_subcategory_displays_only_subcategory_products(self):
        """Test that subcategory displays only products from that subcategory"""
        response = self.client.get(reverse('products:category_products', args=['shirts']))
        self.assertEqual(response.status_code, 200)
        
        # Should display only 5 shirt products
        products = response.context['products']
        self.assertEqual(len(products), 5)
        
        # Verify all products are from shirts category
        for product in products:
            self.assertEqual(product.category, self.subcategory1)
    
    def test_category_not_found_returns_404(self):
        """Test that non-existent category returns 404"""
        response = self.client.get(reverse('products:category_products', args=['nonexistent']))
        self.assertEqual(response.status_code, 404)
    
    def test_inactive_category_returns_404(self):
        """Test that inactive category returns 404"""
        inactive_category = Category.objects.create(
            name='Inactive',
            slug='inactive',
            is_active=False
        )
        
        response = self.client.get(reverse('products:category_products', args=['inactive']))
        self.assertEqual(response.status_code, 404)
    
    def test_pagination_works(self):
        """Test that pagination works correctly"""
        # Create more products to test pagination (need more than 12)
        for i in range(15):
            Product.objects.create(
                name=f'Extra Product {i+1}',
                slug=f'extra-product-{i+1}',
                category=self.parent_category,
                description=f'Extra product {i+1}',
                price=19.99 + i,
                inventory=10,
                is_active=True
            )
        
        # First page should have 12 products
        response = self.client.get(reverse('products:category_products', args=['men']))
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        self.assertEqual(len(products), 12)
        
        # Second page should have remaining products
        response = self.client.get(reverse('products:category_products', args=['men']) + '?page=2')
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        # Total is 3 + 5 + 4 + 15 = 27, so page 2 should have 27 - 12 = 15 products
        self.assertEqual(len(products), 12)
        
        # Third page should have remaining 3 products
        response = self.client.get(reverse('products:category_products', args=['men']) + '?page=3')
        self.assertEqual(response.status_code, 200)
        products = response.context['products']
        self.assertEqual(len(products), 3)
    
    def test_only_active_products_displayed_in_category(self):
        """Test that only active products are displayed in category listing"""
        # Create inactive product
        Product.objects.create(
            name='Inactive Product',
            slug='inactive-product',
            category=self.subcategory1,
            description='This product is inactive',
            price=99.99,
            inventory=5,
            is_active=False
        )
        
        response = self.client.get(reverse('products:category_products', args=['shirts']))
        products = response.context['products']
        
        # Should still have 5 products (inactive not included)
        self.assertEqual(len(products), 5)
        
        # Verify no inactive products
        for product in products:
            self.assertTrue(product.is_active)
    
    def test_two_level_hierarchy_support(self):
        """Test that 2-level category hierarchy is supported"""
        # Verify parent has subcategories
        self.assertEqual(self.parent_category.subcategories.count(), 2)
        
        # Verify subcategories have parent
        self.assertEqual(self.subcategory1.parent, self.parent_category)
        self.assertEqual(self.subcategory2.parent, self.parent_category)
        
        # Verify parent category view includes subcategory products
        response = self.client.get(reverse('products:category_products', args=['men']))
        products = list(response.context['products'])
        
        # Should include products from both subcategories
        shirt_products = [p for p in products if p.category == self.subcategory1]
        pants_products = [p for p in products if p.category == self.subcategory2]
        
        self.assertEqual(len(shirt_products), 5)
        self.assertEqual(len(pants_products), 4)
    
    def test_category_context_data(self):
        """Test that category context data is correct"""
        response = self.client.get(reverse('products:category_products', args=['men']))
        self.assertEqual(response.status_code, 200)
        
        # Verify category in context
        self.assertIn('category', response.context)
        self.assertEqual(response.context['category'].slug, 'men')
        
        # Verify page_obj in context for pagination
        self.assertIn('page_obj', response.context)
    
    def test_products_ordered_by_newest(self):
        """Test that products are ordered by creation date (newest first)"""
        response = self.client.get(reverse('products:category_products', args=['shirts']))
        products = list(response.context['products'])
        
        # Check that products are ordered by newest first
        for i in range(len(products) - 1):
            self.assertGreaterEqual(
                products[i].created_at,
                products[i + 1].created_at
            )
