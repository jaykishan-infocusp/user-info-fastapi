from datetime import datetime

import factory
from faker import Faker

from app.models.profile import GenderEnum, Profile

fake = Faker()


class ProfileFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Profile
        sqlalchemy_session_persistence = "flush"

    user_id = factory.Faker("uuid4")
    name = factory.Faker("name")
    username = factory.Faker("user_name")
    email = factory.Faker("email")

    dob = factory.Faker("date_time_this_century", before_now=True, after_now=False)
    gender = factory.Iterator(list(GenderEnum))  # cycles through enum values
    height = factory.Faker("random_int", min=150, max=200)

    identity_id = factory.Faker("uuid4")
    profile_image_key = factory.LazyAttribute(lambda _: f"profile_images/{fake.uuid4()}.png")

    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = None