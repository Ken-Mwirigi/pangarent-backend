from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings

# 1. Create a Custom Manager to handle standard users vs superusers
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # Automatically set administrative privileges
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True) # Superusers don't need SMS verification
        
        # Automatically assign the admin role so the CLI doesn't ask for it
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


# 2. Your Custom User Model
class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin/Superuser"), # Added to accommodate the SRS requirement 
        ("landlord", "Landlord"),
        ("tenant", "Tenant"),
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True) 
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    # We remove 'role' from REQUIRED_FIELDS because our CustomUserManager handles it for superusers,
    # and your registration views will handle it for landlords/tenants.
    REQUIRED_FIELDS = ['username', 'phone_number'] 

    # Link the custom manager to the model
    objects = CustomUserManager()

    def __str__(self):
        return self.email

# 3. Landlord Profile
class LandlordProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='landlord_profile'
    )
    full_name = models.CharField(max_length=255)
    
    def __str__(self):
        return self.full_name


# ... your existing User and LandlordProfile models ...

class OTPVerification(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='otp_profile'
    )
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.otp_code}"