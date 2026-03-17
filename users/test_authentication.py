from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class UserLoginTests(TestCase):
    """Test user login functionality"""
    
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('users:login')
        
        # Create a verified user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='TestPass123'
        )
        self.user.email_verified = True
        self.user.save()
        
        # Create a user with phone number
        self.phone_user = User.objects.create_user(
            username='phone@example.com',
            email='phone@example.com',
            phone_number='+1234567890',
            password='TestPass123'
        )
        self.phone_user.email_verified = True
        self.phone_user.save()
    
    def test_login_form_displays(self):
        """Test that login form is displayed"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login to FabVibe')
        self.assertContains(response, 'Email or Phone Number')
        self.assertContains(response, 'Password')
    
    def test_valid_login_with_email(self):
        """Test successful login with email"""
        data = {
            'username': 'test@example.com',
            'password': 'TestPass123',
        }
        response = self.client.post(self.login_url, data)
        
        # Check user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.email, 'test@example.com')
        
        # Check redirect to home (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('products:home'))
    
    def test_valid_login_with_phone(self):
        """Test successful login with phone number"""
        data = {
            'username': '+1234567890',
            'password': 'TestPass123',
        }
        response = self.client.post(self.login_url, data)
        
        # Check user is logged in
        self.assertTrue(response.wsgi_request.user.is_authenticated)
        self.assertEqual(response.wsgi_request.user.phone_number, '+1234567890')
        
        # Check redirect to home (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('products:home'))
    
    def test_invalid_email_login(self):
        """Test login with invalid email"""
        data = {
            'username': 'wrong@example.com',
            'password': 'TestPass123',
        }
        response = self.client.post(self.login_url, data)
        
        # Check user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Check generic error message
        self.assertContains(response, 'Invalid credentials')
    
    def test_invalid_password_login(self):
        """Test login with invalid password"""
        data = {
            'username': 'test@example.com',
            'password': 'WrongPassword',
        }
        response = self.client.post(self.login_url, data)
        
        # Check user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Check generic error message (doesn't reveal which credential was wrong)
        self.assertContains(response, 'Invalid credentials')
    
    def test_invalid_phone_login(self):
        """Test login with invalid phone number"""
        data = {
            'username': '+9999999999',
            'password': 'TestPass123',
        }
        response = self.client.post(self.login_url, data)
        
        # Check user is not logged in
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Check generic error message
        self.assertContains(response, 'Invalid credentials')
    
    def test_login_redirect_to_next(self):
        """Test login redirects to next parameter"""
        data = {
            'username': 'test@example.com',
            'password': 'TestPass123',
        }
        response = self.client.post(self.login_url + '?next=/cart/', data)
        
        # Check redirect to next URL (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/cart/')
    
    def test_authenticated_user_redirect(self):
        """Test authenticated user is redirected from login page"""
        # Login first
        self.client.login(username='test@example.com', password='TestPass123')
        
        # Try to access login page
        response = self.client.get(self.login_url)
        
        # Check redirect to home (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('products:home'))


class UserLogoutTests(TestCase):
    """Test user logout functionality"""
    
    def setUp(self):
        self.client = Client()
        self.logout_url = reverse('users:logout')
        
        # Create a verified user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            password='TestPass123'
        )
        self.user.email_verified = True
        self.user.save()
    
    def test_logout_terminates_session(self):
        """Test logout terminates user session"""
        # Login first
        self.client.login(username='test@example.com', password='TestPass123')
        
        # Verify user is logged in by checking session
        self.assertIn('_auth_user_id', self.client.session)
        
        # Logout
        response = self.client.get(self.logout_url)
        
        # Check user is logged out
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        
        # Check redirect to home (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('products:home'))
    
    def test_logout_success_message(self):
        """Test logout displays success message"""
        # Login first
        self.client.login(username='test@example.com', password='TestPass123')
        
        # Logout (don't follow redirect to avoid template error)
        response = self.client.get(self.logout_url)
        
        # Check success message in session
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('logged out successfully', str(messages[0]))
    
    def test_logout_when_not_logged_in(self):
        """Test logout when user is not logged in"""
        # Logout without logging in
        response = self.client.get(self.logout_url)
        
        # Should still redirect to home (don't follow to avoid template error)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('products:home'))


class PasswordResetTests(TestCase):
    """Test password reset functionality"""
    
    def setUp(self):
        self.client = Client()
        self.password_reset_url = reverse('users:password_reset')
        
        # Create a verified user
        self.user = User.objects.create_user(
            username='test@example.com',
            email='test@example.com',
            first_name='Test',
            last_name='User',
            password='OldPass123'
        )
        self.user.email_verified = True
        self.user.save()
    
    def test_password_reset_form_displays(self):
        """Test that password reset form is displayed"""
        response = self.client.get(self.password_reset_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reset Password')
        self.assertContains(response, 'Email Address')
    
    def test_password_reset_request_with_valid_email(self):
        """Test password reset request with valid email sends email"""
        data = {'email': 'test@example.com'}
        response = self.client.post(self.password_reset_url, data)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:login'))
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('Password reset link has been sent', str(messages[0]))
    
    def test_password_reset_request_with_invalid_email(self):
        """Test password reset request with invalid email doesn't reveal user existence"""
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(self.password_reset_url, data)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:login'))
        
        # Check generic success message (doesn't reveal if email exists)
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('If an account exists', str(messages[0]))
    
    def test_password_reset_request_with_invalid_email_format(self):
        """Test password reset request with invalid email format"""
        data = {'email': 'not-an-email'}
        response = self.client.post(self.password_reset_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Enter a valid email address')
    
    def test_password_reset_confirm_with_valid_token(self):
        """Test password reset confirmation with valid token"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Access reset confirm page
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        response = self.client.get(reset_confirm_url)
        
        # Check page displays
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Set New Password')
        self.assertContains(response, 'Password Requirements')
    
    def test_password_reset_confirm_with_invalid_token(self):
        """Test password reset confirmation with invalid token"""
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate invalid token
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = 'invalid-token-123'
        
        # Access reset confirm page
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': invalid_token})
        response = self.client.get(reset_confirm_url)
        
        # Check error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Reset Link')
        self.assertContains(response, 'invalid or has expired')
    
    def test_password_reset_confirm_with_invalid_uid(self):
        """Test password reset confirmation with invalid user ID"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token with invalid user ID
        token = default_token_generator.make_token(self.user)
        invalid_uid = urlsafe_base64_encode(force_bytes(99999))
        
        # Access reset confirm page
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': invalid_uid, 'token': token})
        response = self.client.get(reset_confirm_url)
        
        # Check error message
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid Reset Link')
    
    def test_password_update_with_valid_data(self):
        """Test password update with valid new password"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit new password
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'NewPass123',
            'new_password2': 'NewPass123',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Check redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:login'))
        
        # Check success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn('password has been reset successfully', str(messages[0]))
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewPass123'))
        self.assertFalse(self.user.check_password('OldPass123'))
    
    def test_password_update_with_mismatched_passwords(self):
        """Test password update with mismatched passwords"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit mismatched passwords
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'NewPass123',
            'new_password2': 'DifferentPass123',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        # Check that form has errors
        self.assertIn('form', response.context)
        self.assertTrue(response.context['form'].errors)
    
    def test_password_complexity_validation_too_short(self):
        """Test password complexity validation - too short"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit password that's too short
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'Pass1',
            'new_password2': 'Pass1',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'at least 8 characters')
    
    def test_password_complexity_validation_no_uppercase(self):
        """Test password complexity validation - no uppercase letter"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit password without uppercase
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'password123',
            'new_password2': 'password123',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'uppercase letter')
    
    def test_password_complexity_validation_no_lowercase(self):
        """Test password complexity validation - no lowercase letter"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit password without lowercase
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'PASSWORD123',
            'new_password2': 'PASSWORD123',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lowercase letter')
    
    def test_password_complexity_validation_no_number(self):
        """Test password complexity validation - no number"""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        # Generate token
        token = default_token_generator.make_token(self.user)
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        
        # Submit password without number
        reset_confirm_url = reverse('users:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'new_password1': 'PasswordOnly',
            'new_password2': 'PasswordOnly',
        }
        response = self.client.post(reset_confirm_url, data)
        
        # Should stay on the same page with form errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'at least one number')
