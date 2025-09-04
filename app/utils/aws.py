import boto3
from botocore.config import Config

from app.core.config import settings


class AWSHelper:
    """
    A centralized AWS helper for managing boto3 clients.
    Provides convenience methods to fetch Cognito and S3 clients.
    """

    def __init__(self):
        self._session = boto3.session.Session(
            region_name=settings.AWS_REGION_NAME,
        )
        self._config = Config(retries={"max_attempts": 3, "mode": "standard"})

    def get_s3(self):
        """
        Return a boto3 S3 client.
        """
        return self._session.client("s3", config=self._config)

    def get_cognito(self):
        """
        Return a boto3 Cognito Identity Provider client.
        """
        return self._session.client("cognito-idp", config=self._config)

    def get_cognito_identity(self):
        """
        Return Cognito Identity id client
        """
        return self._session.client(
            "cognito-identity", region_name=settings.AWS_REGION_NAME
        )


aws_helper = AWSHelper()
