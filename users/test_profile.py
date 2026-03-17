from django.test import TestCase, Client
from django.urls import reverse
from users.models import User, Address


class ProfileViewTest(TestCase):
    """Test cases for user profile management"""
    
    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123',
            first_name='Test',
            last_name='User',
            phone_number='+1234567890'
        )
        self.user.email_verified = True
        self.user.save()
    
    def test_profile_view_requires_login(self):
        """Test that profile view requires authentication"""
        response = self.client.get(reverse('users:profile'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_profile_view_displays_user_info(self):
        """Test that profile view displays current user information"""
        self.client.login(username='testuser@example.com', password='TestPass123')
        response = self.client.get(reverse('users:profile'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test')
        self.assertContains(response, 'User')
        self.assertContains(response, 'testuser@example.com')
    
    def test_profile_update_name(self):
        """Test updating user name"""
        self.client.login(username='testuser@example.com', password='TestPass123')
        
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+1234567890'
        })
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(response.status_code, 302)  # Redirect after success
    
    def test_profile_update_phone_number(self):
        """Test updating phone number with validation"""
        self.client.login(username='testuser@example.com', password='TestPass123')
        
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+9876543210'
        })
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+9876543210')
        self.assertEqual(response.status_code, 302)
    
    def test_profile_invalid_phone_number(self):
        """Test that invalid phone number is rejected"""
        self.client.login(username='testuser@example.com', password='TestPass123')
        
        response = self.client.post(reverse('users:profile'), {
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': 'invalid'
        })
        
        self.assertEqual(response.status_code, 200)  # Stay on page with errors
        self.assertFormError(response, 'form', 'phone_number', 
                           "Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")


class AddressManagementTest(TestCase):
    """Test cases for address management"""
    
    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='TestPass123',
            first_name='Test',
            last_name='User'
        )
        self.user.email_verified = True
        self.user.save()
        self.client.login(username='testuser@example.com', password='TestPass123')
    
    def test_add_address(self):
        """Test adding a new shipping address"""
        response = self.client.post(reverse('users:add_address'), {
            'full_name': 'Test User',
            'phone_number': '+1234567890',
            'address_line1': '123 Test Street',
            'address_line2': 'Apt 4B',
            'city': 'Test City',
            'state': 'Test State',
            'postal_code': '12345',
            'country': 'India',
            'is_default': True
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertEqual(Address.objects.filter(user=self.user).count(), 1)
        
        address = Address.objects.get(user=self.user)
        self.assertEqual(address.full_name, 'Test User')
        self.assertEqual(address.city, 'Test City')
        self.assertTrue(address.is_default)
    
    def test_edit_address(self):
        """Test editing an existing address"""
        address = Address.objects.create(
            user=self.user,
            full_name='Original Name',
            phone_number='+1234567890',
            address_line1='123 Original St',
            city='Original City',
            state='Original State',
            postal_code='12345',
            country='India'
        )
        
        response = self.client.post(reverse('users:edit_address', args=[address.id]), {
            'full_name': 'Updated Name',
            'phone_number': '+1234567890',
            'address_line1': '456 Updated St',
            'address_line2': '',
            'city': 'Updated City',
            'state': 'Updated State',
            'postal_code': '54321',
            'country': 'India',
            'is_default': False
        })
        
        self.assertEqual(response.status_code, 302)
        address.refresh_from_db()
        self.assertEqual(address.full_name, 'Updated Name')
        self.assertEqual(address.city, 'Updated City')
    
    def test_delete_address(self):
        """Test deleting an address"""
        address = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 Test St',
            city='Test City',
            state='Test State',
            postal_code='12345',
            country='India'
        )
        
        response = self.client.post(reverse('users:delete_address', args=[address.id]))
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Address.objects.filter(user=self.user).count(), 0)
    
    def test_multiple_addresses_support(self):
        """Test that users can have multiple addresses"""
        # Create first address
        Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 First St',
            city='City 1',
            state='State 1',
            postal_code='12345',
            country='India',
            is_default=True
        )
        
        # Create second address
        Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='456 Second St',
            city='City 2',
            state='State 2',
            postal_code='54321',
            country='India',
            is_default=False
        )
        
        self.assertEqual(Address.objects.filter(user=self.user).count(), 2)
        
        # Verify profile page displays both addresses
        response = self.client.get(reverse('users:profile'))
        self.assertContains(response, '123 First St')
        self.assertContains(response, '456 Second St')
    
    def test_default_address_management(self):
        """Test that only one address can be default"""
        # Create first default address
        address1 = Address.objects.create(
            user=self.user,
            full_name='Test User',
            phone_number='+1234567890',
            address_line1='123 First St',
            city='City 1',
            state='State 1',
            postal_code='12345',
            country='India',
            is_default=True
        )
        
        # Create second address and set as default
        self.client.post(reverse('users:add_address'), {
            'full_name': 'Test User',
            'phone_number': '+1234567890',
            'address_line1': '456 Second St',
            'address_line2': '',
            'city': 'City 2',
            'state': 'State 2',
            'postal_code': '54321',
            'country': 'India',
            'is_default': True
        })
        
        # Verify first address is no longer default
        address1.refresh_from_db()
        self.assertFalse(address1.is_default)
        
        # Verify second address is default
        address2 = Address.objects.get(address_line1='456 Second St')
        self.assertTrue(address2.is_default)
