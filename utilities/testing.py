"""useful utility methods"""
import json

from django.conf import settings
from dlkit_django.primordium import Type
import dlkit_django.configs

from rest_framework_httpsignature.authentication import SignatureAuthentication


class APISignatureAuthentication(SignatureAuthentication):
    """
    Adapted from
    https://github.com/etoccalino/django-rest-framework-httpsignature/blob/master/rest_framework_httpsignature/tests.py
    """
    API_KEY_HEADER = 'X-Api-Key'
    def __init__(self, user):
        self.user = user

    def fetch_user_data(self, api_key):
        return (self.user, str(self.user.private_key))

def calculate_signature(auth, headers, method, path):
    """
    Should return the encoded signature from an HTTPSignatureAuth object
    Need to use the .sign(headers, method, path) of the header_signer object
    in auth
    """
    signed_headers = auth.header_signer.sign(headers, method=method, path=path)
    return signed_headers['authorization']


def configure_test_bucket():
    """use test settings, not the production settings"""
    dlkit_django.configs.AWS_ADAPTER_1 = {
        'id': 'aws_adapter_configuration_1',
        'displayName': 'AWS Adapter Configuration',
        'description': 'Configuration for AWS Adapter',
        'parameters': {
            'implKey': {
                'syntax': 'STRING',
                'displayName': 'Implementation Key',
                'description': 'Implementation key used by Runtime for class loading',
                'values': [
                    {'value': 'aws_adapter', 'priority': 1}
                ]
            },
            'cloudFrontPublicKey': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Public Key',
                'description': 'Public key for Amazon CloudFront service.',
                'values': [
                    {'value': settings.CLOUDFRONT_PUBLIC_KEY, 'priority': 1}
                ]
            },
            'cloudFrontPrivateKey': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Private Key',
                'description': 'Private key for Amazon CloudFront service.',
                'values': [
                    {'value': settings.CLOUDFRONT_PRIVATE_KEY, 'priority': 1}
                ]
            },
            'cloudFrontSigningKeypairId': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Signing Keypair ID',
                'description': 'Signing keypair id for Amazon CloudFront service.',
                'values': [
                    {'value': settings.CLOUDFRONT_SIGNING_KEYPAIR_ID, 'priority': 1}
                ]
            },
            'cloudFrontSigningPrivateKeyFile': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Signing Private Key File',
                'description': 'Signing Private Key File for Amazon CloudFront service.',
                'values': [
                    {'value': settings.CLOUDFRONT_SIGNING_PRIVATE_KEY_FILE, 'priority': 1}
                ]
            },
            'cloudFrontDistro': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Distro',
                'description': 'CloudFront Distr-o-bution.',
                'values': [
                    {'value': settings.CLOUDFRONT_DISTRO, 'priority': 1}
                ]
            },
            'cloudFrontDistroId': {
                'syntax': 'STRING',
                'displayName': 'CloudFront Distro Id',
                'description': 'CloudFront Distr-o-bution Id.',
                'values': [
                    {'value': settings.CLOUDFRONT_DISTRO_ID, 'priority': 1}
                ]
            },
            'S3PrivateKey': {
                'syntax': 'STRING',
                'displayName': 'S3 Private Key',
                'description': 'Private Key for Amazon S3.',
                'values': [
                    {'value': settings.S3_PRIVATE_KEY, 'priority': 1}
                ]
            },
            'S3PublicKey': {
                'syntax': 'STRING',
                'displayName': 'S3 Public Key',
                'description': 'Public Key for Amazon S3.',
                'values': [
                    {'value': settings.S3_PUBLIC_KEY, 'priority': 1}
                ]
            },
            'S3Bucket': {
                'syntax': 'STRING',
                'displayName': 'S3 Bucket',
                'description': 'Bucket for Amazon S3.',
                'values': [
                    {'value': settings.S3_BUCKET, 'priority': 1}
                ]
            },
            'repositoryProviderImpl': {
                'syntax': 'STRING',
                'displayName': 'Repository Provider Implementation',
                'description': 'Implementation for repository service provider',
                'values': [
                    {'value': 'MONGO_1', 'priority': 1}
                ]
            },
        }
    }

    dlkit_django.configs.MONGO_1 = {
        'id': 'mongo_configuration_1',
        'displayName': 'Mongo Configuration',
        'description': 'Configuration for Mongo Implementation',
        'parameters': {
            'implKey': {
                'syntax': 'STRING',
                'displayName': 'Implementation Key',
                'description': 'Implementation key used by Runtime for class loading',
                'values': [
                    {'value': 'mongo', 'priority': 1}
                ]
            },
            'authority': {
                'syntax': 'STRING',
                'displayName': 'Mongo Authority',
                'description': 'Authority.',
                'values': [
                    {'value': settings.DLKIT_AUTHORITY, 'priority': 1}
                ]
            },
            'mongoDBNamePrefix': {
                'syntax': 'STRING',
                'displayName': 'Mongo DB Name Prefix',
                'description': 'Prefix for naming mongo databases.',
                'values': [
                    {'value': settings.DLKIT_MONGO_DB_PREFIX, 'priority': 1}
                ]
            },
            'mongoHostURI': {
                'syntax': 'STRING',
                'displayName': 'Mongo Host URI',
                'description': 'URI for setting the MongoClient host.',
                'values': [
                    {'value': settings.MONGO_HOST_URI, 'priority': 1}
                ]
            },
            'repositoryProviderImpl': {
                'syntax': 'STRING',
                'displayName': 'Repository Provider Implementation',
                'description': 'Implementation for repository service provider',
                'values': [
                    {'value': 'AWS_ADAPTER_1', 'priority': 1}
                ]
            },
            'assetContentRecordTypeForFiles': {
                'syntax': 'TYPE',
                'displayName': 'Asset Content Type for Files',
                'description': 'Asset Content Type for Records that store Files in a repository',
                'values': [
                    {'value': Type(**{
                       'authority': 'odl.mit.edu',
                       'namespace': 'asset_content_record_type',
                       'identifier': 'amazon-web-services'
                    }), 'priority': 1}
                ]
            },
        }
    }

def create_test_bank(test_instance):
    """
    helper method to create a test assessment bank
    """
    test_endpoint = '/api/v2/assessment/banks/'
    test_instance.login()
    payload = {
        "name": "a test bank",
        "description": "for testing"
    }
    req = test_instance.client.post(test_endpoint, payload, format='json')
    return json.loads(req.content)

def create_test_request(test_user):
    from django.http import HttpRequest
    from django.conf import settings
    from django.utils.importlib import import_module
    #http://stackoverflow.com/questions/16865947/django-httprequest-object-has-no-attribute-session
    test_request = HttpRequest()
    engine = import_module(settings.SESSION_ENGINE)
    session_key = None
    test_request.user = test_user
    test_request.session = engine.SessionStore(session_key)
    return test_request
