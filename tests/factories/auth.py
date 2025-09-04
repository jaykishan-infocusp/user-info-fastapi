# tests/factories/auth.py
import factory
from app.schemas.auth import SignupRequest, ConfirmSignupRequest, LoginRequest, RefreshRequest

class SignupRequestFactory(factory.Factory):
    class Meta:
        model = SignupRequest

    username = factory.Faker("user_name")
    email = factory.Faker("email")
    name = factory.Faker("name")
    password = factory.Faker("password")


class ConfirmSignupRequestFactory(factory.Factory):
    class Meta:
        model = ConfirmSignupRequest

    username = factory.Faker("user_name")
    code = factory.Faker("numerify", text="######")


class LoginRequestFactory(factory.Factory):
    class Meta:
        model = LoginRequest

    username = factory.Faker("email")
    password = factory.Faker("password")


class RefreshRequestFactory(factory.Factory):
    class Meta:
        model = RefreshRequest

    refresh_token = factory.Faker("uuid4")
