from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Category, Product
from cart.models import Cart, CartItem

User = get_user_model()


class NavigationHeaderTest(TestCase):
    """Test navigation header functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='testpass123',
            phone_number='+1234567890',
            email_verified=True
        )
        
        # Create parent categories
        self.men_category = Category.objects.create(
            name='Men',
            slug='men',
            is_active=True
        )
        
        self.women_category = Category.objects.create(
            name='Women',
            slug='women',
            is_active=True
        )
        
        # Create subcategories
        self.men_shirts = Category.objects.create(
            name='Shirts',
            slug='men-shirts',
            parent=self.men_category,
            is_active=True
        )
        
        self.women_dresses = Category.objects.create(
            name='Dresses',
            slug='women-dresses',
            parent=self.women_category,
            is_active=True
        )
        
        # Create test product
        self.product = Product.objects.create(
            name='Test Shirt',
            slug='test-shirt',
            category=self.men_shirts,
            description='A test shirt',
            price=29.99,
            inventory=10,
            is_active=True
        )
    
    def test_categories_displayed_in_navigation(self):
        """Test that categories are displayed in navigation dropdown"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Check that parent categories are in the response
        self.assertContains(response, 'Men')
        self.assertContains(response, 'Women')
    
    def test_subcategories_displayed_in_navigation(self):
        """Test that subcategories are displayed in navigation dropdown"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Check that subcategories are in the response
        self.assertContains(response, 'Shirts')
        self.assertContains(response, 'Dresses')
    
    def test_category_links_are_correct(self):
        """Test that category links point to correct URLs"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Check that category URLs are present
        men_url = reverse('products:category_products', kwargs={'category_slug': 'men'})
        shirts_url = reverse('products:category_products', kwargs={'category_slug': 'men-shirts'})
        
        self.assertContains(response, men_url)
        self.assertContains(response, shirts_url)
    
    def test_cart_count_badge_for_guest_user(self):
        """Test that cart count badge is not displayed for guest users with empty cart"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Cart count should be 0 for guest users with no items
        self.assertNotContains(response, '<span class="badge bg-primary">')
    
    def test_cart_count_badge_for_authenticated_user(self):
        """Test that cart count badge displays correct count for authenticated users"""
        # Login user
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart with items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, size='M', quantity=2)
        
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Cart count badge should be displayed with count of 1 (1 item type)
        self.assertContains(response, '<span class="badge bg-primary">1</span>')
    
    def test_user_authentication_status_guest(self):
        """Test that login/register links are shown for guest users"""
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Should show login and register links
        self.assertContains(response, 'Login')
        self.assertContains(response, 'Register')
        self.assertNotContains(response, 'Logout')
    
    def test_user_authentication_status_authenticated(self):
        """Test that user menu is shown for authenticated users"""
        # Login user
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Should show user email and logout link
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Logout')
        self.assertContains(response, 'Profile')
        self.assertNotContains(response, 'Register')
    
    def test_inactive_categories_not_displayed(self):
        """Test that inactive categories are not displayed in navigation"""
        # Create inactive category
        inactive_category = Category.objects.create(
            name='Inactive Category',
            slug='inactive',
            is_active=False
        )
        
        response = self.client.get(reverse('products:home'))
        self.assertEqual(response.status_code, 200)
        
        # Inactive category should not be in the response
        self.assertNotContains(response, 'Inactive Category')
    
    def test_navigation_header_present_on_all_pages(self):
        """Test that navigation header is present on all pages using base template"""
        # Test on different pages
        pages = [
            reverse('products:home'),
            reverse('users:login'),
            reverse('users:register'),
        ]
        
        for page_url in pages:
            response = self.client.get(page_url)
            
            # Navigation should be present
            self.assertContains(response, 'FabVibe')
            self.assertContains(response, 'Categories')
