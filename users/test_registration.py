from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone

User = get_user_model()


class UserRegistrationTests(TestCase):
    """Test user registration functionality"""
    
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('users:register')
        self.verify_otp_url = reverse('users:verify_otp')
    
    def test_registration_form_displays(self):
        """Test that registration form is displayed"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
        self.assertContains(response, 'Email')
        self.assertContains(response, 'Password')
    
    def test_valid_registration_with_email(self):
        """Test successful registration with valid email"""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check user was created
        self.assertTrue(User.objects.filter(email='test@example.com').exists())
        user = User.objects.get(email='test@example.com')
        
        # Check password is hashed
        self.assertNotEqual(user.password, 'TestPass123')
        self.assertTrue(user.check_password('TestPass123'))
        
        # Check OTP was generated
        self.assertIsNotNone(user.otp_code)
        self.assertEqual(len(user.otp_code), 6)
        self.assertIsNotNone(user.otp_expiry)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify', mail.outbox[0].subject)
        
        # Check redirect to OTP verification
        self.assertRedirects(response, self.verify_otp_url)
    
    def test_valid_registration_with_phone(self):
        """Test successful registration with phone number"""
        data = {
            'email': 'test@example.com',
            'phone_number': '+1234567890',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check user was created with phone
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.phone_number, '+1234567890')
    
    def test_duplicate_email_validation(self):
        """Test that duplicate email is rejected"""
        # Create first user
        User.objects.create_user(
            username='existing@example.com',
            email='existing@example.com',
            password='TestPass123'
        )
        
        # Try to register with same email
        data = {
            'email': 'existing@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check error message
        self.assertContains(response, 'This email is already registered')
        
        # Check only one user exists
        self.assertEqual(User.objects.filter(email='existing@example.com').count(), 1)
    
    def test_duplicate_phone_validation(self):
        """Test that duplicate phone number is rejected"""
        # Create first user
        User.objects.create_user(
            username='user1@example.com',
            email='user1@example.com',
            phone_number='+1234567890',
            password='TestPass123'
        )
        
        # Try to register with same phone
        data = {
            'email': 'user2@example.com',
            'phone_number': '+1234567890',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check error message
        self.assertContains(response, 'This phone number is already registered')
    
    def test_invalid_email_format(self):
        """Test that invalid email format is rejected"""
        data = {
            'email': 'invalid-email',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check no user was created
        self.assertFalse(User.objects.filter(email='invalid-email').exists())
        self.assertContains(response, 'Enter a valid email address')
    
    def test_invalid_phone_format(self):
        """Test that invalid phone format is rejected"""
        data = {
            'email': 'test@example.com',
            'phone_number': 'invalid-phone',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'TestPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check error message
        self.assertContains(response, 'Phone number must be entered in the format')
    
    def test_password_mismatch(self):
        """Test that mismatched passwords are rejected"""
        data = {
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'TestPass123',
            'password2': 'DifferentPass123',
        }
        response = self.client.post(self.register_url, data)
        
        # Check no user was created
        self.assertFalse(User.objects.filter(email='test@example.com').exists())


class OTPVerificationTests(TestCase):
    """Test OTP verification functionality"""
    
    def setUp(self):
        self.client = Client()
        self.verify_otp_url = reverse('users:verify_otp')
        self.resend_otp_url = reverse('users:resend_otp')
        
        # Create a user with OTP
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='TestPass123'
        )
        self.otp_code = self.user.generate_otp()
    
    def test_valid_otp_verification(self):
        """Test successful OTP verification"""
        # Set session
        session = self.client.session
        session['pending_user_id'] = self.user.id
        session.save()
        
        # Submit valid OTP
        response = self.client.post(self.verify_otp_url, {'otp_code': self.otp_code})
        
        # Check user is verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertIsNone(self.user.otp_code)
        
        # Check user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
    
    def test_invalid_otp_code(self):
        """Test invalid OTP code is rejected"""
        # Set session
        session = self.client.session
        session['pending_user_id'] = self.user.id
        session.save()
        
        # Submit invalid OTP
        response = self.client.post(self.verify_otp_url, {'otp_code': '000000'})
        
        # Check user is not verified
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)
        
        # Check error message
        self.assertContains(response, 'Invalid OTP code')
    
    def test_expired_otp(self):
        """Test expired OTP is rejected"""
        # Set session
        session = self.client.session
        session['pending_user_id'] = self.user.id
        session.save()
        
        # Expire the OTP
        self.user.otp_expiry = timezone.now() - timezone.timedelta(minutes=1)
        self.user.save()
        
        # Submit OTP
        response = self.client.post(self.verify_otp_url, {'otp_code': self.otp_code})
        
        # Check error message
        self.assertContains(response, 'OTP has expired')
    
    def test_resend_otp(self):
        """Test OTP can be resent"""
        # Set session
        session = self.client.session
        session['pending_user_id'] = self.user.id
        session.save()
        
        old_otp = self.user.otp_code
        
        # Clear mail outbox
        mail.outbox = []
        
        # Resend OTP
        response = self.client.get(self.resend_otp_url)
        
        # Check new OTP was generated
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.otp_code, old_otp)
        
        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        
        # Check redirect
        self.assertRedirects(response, self.verify_otp_url)
