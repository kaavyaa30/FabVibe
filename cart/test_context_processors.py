from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from cart.models import Cart, CartItem
from cart.context_processors import cart_count
from products.models import Product, Category

User = get_user_model()


class CartContextProcessorTestCase(TestCase):
    """Test cart context processor"""
    
    def setUp(self):
        """Set up test data"""
        self.factory = RequestFactory()
        self.client = Client()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test category and product
        self.category = Category.objects.create(
            name='Test Category',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Test Product',
            slug='test-product',
            category=self.category,
            description='Test description',
            price=99.99,
            inventory=100
        )
    
    def test_cart_count_authenticated_user_with_items(self):
        """Test cart count for authenticated user with items"""
        # Create cart with items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, size='M', quantity=2)
        CartItem.objects.create(cart=cart, product=self.product, size='L', quantity=1)
        
        # Create request
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        
        # Get context
        context = cart_count(request)
        
        self.assertEqual(context['cart_count'], 2)
    
    def test_cart_count_authenticated_user_empty_cart(self):
        """Test cart count for authenticated user with empty cart"""
        request = self.factory.get('/')
        request.user = self.user
        request.session = {}
        
        context = cart_count(request)
        
        self.assertEqual(context['cart_count'], 0)
    
    def test_cart_count_guest_user_with_items(self):
        """Test cart count for guest user with items"""
        # Create session cart
        session = self.client.session
        session.create()
        session.save()
        
        cart = Cart.objects.create(session_key=session.session_key)
        CartItem.objects.create(cart=cart, product=self.product, size='M', quantity=1)
        
        # Create request
        request = self.factory.get('/')
        request.user = User()  # Anonymous user
        request.session = session
        
        context = cart_count(request)
        
        self.assertEqual(context['cart_count'], 1)
    
    def test_cart_count_guest_user_no_session(self):
        """Test cart count for guest user without session"""
        request = self.factory.get('/')
        request.user = User()  # Anonymous user
        request.session = self.client.session
        
        context = cart_count(request)
        
        self.assertEqual(context['cart_count'], 0)
    
    def test_cart_count_in_template(self):
        """Test cart count appears in rendered template"""
        self.client.login(email='test@example.com', password='testpass123')
        
        # Create cart with items
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, size='M', quantity=1)
        
        # Access any page
        response = self.client.get('/cart/')
        
        # Check that cart count is in the response
        self.assertContains(response, 'badge')
        self.assertContains(response, '1')
