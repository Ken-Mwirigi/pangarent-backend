import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

# @pytest.mark.django_db gives this test permission to create a temporary, 
# blank database just for testing, which deletes itself when finished!
@pytest.mark.django_db
def test_landlord_registration_creates_unverified_user():
    client = APIClient()
    
    # 1. The fake data coming from React
    payload = {
        "email": "testlandlord@pangarent.com",
        "phone_number": "0712345678",
        "full_name": "Test Landlord",
        "password": "SecurePassword123",
        "confirm_password": "SecurePassword123"
    }
    
    # 2. Hit your actual API endpoint 
    # (Assuming your auth urls are routed through /api/auth/...)
    response = client.post('/api/auth/register/landlord/', payload)
    
    # 3. Check if the API responded with 201 Created
    assert response.status_code == 201
    assert "Account created" in response.data['message']
    
    # 4. Check the Database to ensure the user was actually saved
    user_exists = User.objects.filter(email="testlandlord@pangarent.com").exists()
    assert user_exists is True
    
    # 5. Ensure the user is locked out until they verify their OTP
    created_user = User.objects.get(email="testlandlord@pangarent.com")
    assert created_user.is_verified is False
    assert created_user.role == 'landlord'

@pytest.mark.django_db
def test_verified_user_can_login_and_get_tokens():
    client = APIClient()
    
    # 1. SETUP: Create a verified user in the test database
    User.objects.create_user(
        email="verified@pangarent.com",
        phone_number="0799999999",
        password="ValidPassword123",
        role="landlord",
        is_verified=True # <-- They are verified!
    )
    
    # 2. ACTION: Try to log in
    response = client.post('/api/auth/login/', {
        "email": "verified@pangarent.com",
        "password": "ValidPassword123"
    })
    
    # 3. ASSERT: Did we get the JWT tokens?
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data
    assert response.data["role"] == "landlord"


@pytest.mark.django_db
def test_unverified_user_cannot_login():
    client = APIClient()
    
    # 1. SETUP: Create an UNVERIFIED user
    User.objects.create_user(
        email="unverified@pangarent.com",
        phone_number="0788888888",
        password="ValidPassword123",
        role="landlord",
        is_verified=False # <-- Not verified!
    )
    
    # 2. ACTION: Try to log in
    response = client.post('/api/auth/login/', {
        "email": "unverified@pangarent.com",
        "password": "ValidPassword123"
    })
    
    # 3. ASSERT: They should be blocked!
    assert response.status_code == 401 # 401 Unauthorized
    assert "Account is not verified" in str(response.data)