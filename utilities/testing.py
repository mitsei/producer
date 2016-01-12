"""useful utility methods"""
import os
import json
import envoy

import dlkit_django.configs

from django.conf import settings
from django.test.utils import override_settings
from django.contrib.auth.models import User

from dlkit_django.primordium import Type, Id

from minimocktest import MockTestCase

from rest_framework.test import APITestCase, APIClient

from utilities import general as gutils
from utilities import grading as grutils

PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
ABS_PATH = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))


@override_settings(DLKIT_MONGO_DB_PREFIX='test_producer_',
                   CLOUDFRONT_DISTRO='d1v4o60a4yrgi8.cloudfront.net',
                   CLOUDFRONT_DISTRO_ID='E1OEKZHRUO35M9',
                   S3_BUCKET='mitodl-repository-test',
                   CELERY_ALWAYS_EAGER=True,
                   TEST=True)
class DjangoTestCase(APITestCase, MockTestCase):
    """
    A TestCase class that combines minimocktest and django.test.TestCase

    http://pykler.github.io/MiniMockTest/
    """
    def _pre_setup(self):
        APITestCase._pre_setup(self)
        MockTestCase.setUp(self)
        # optional: shortcut client handle for quick testing
        self.client = APIClient()

    def _post_teardown(self):
        MockTestCase.tearDown(self)
        APITestCase._post_teardown(self)

    def code(self, _req, _code):
        self.assertEqual(_req.status_code, _code)

    def created(self, _req):
        self.code(_req, 201)

    def deleted(self, _req):
        self.code(_req, 204)

    def filename(self, file_):
        try:
            return file_.name.split('/')[-1].split('.')[0]
        except AttributeError:
            return file_.split('/')[-1].split('.')[0]

    def is_cloudfront_url(self, _url):
        self.assertIn(
            'https://d1v4o60a4yrgi8.cloudfront.net/',
            _url
        )

        expected_params = ['?Expires=','&Signature=','&Key-Pair-Id=APKAIGRK7FPIAJR675NA']

        for param in expected_params:
            self.assertIn(
                param,
                _url
            )

    def json(self, _req):
        return json.loads(_req.content)

    def login(self, non_instructor=False):
        if non_instructor:
            self.client.login(username=self.student_name, password=self.student_password)
        else:
            self.client.login(username=self.username, password=self.password)

    def message(self, _req, _msg):
        self.assertIn(_msg, str(_req.content))

    def ok(self, _req):
        self.assertEqual(_req.status_code, 200)

    def setUp(self):
        envoy.run('mongo test_producer_assessment --eval "db.dropDatabase()"')
        envoy.run('mongo test_producer_grading --eval "db.dropDatabase()"')
        envoy.run('mongo test_producer_repository --eval "db.dropDatabase()"')

        configure_test_bucket()
        self.base_url = '/api/v1/'
        self.username = 'cjshaw@mit.edu'
        self.password = 'jinxem'
        self.user = User.objects.create_user(username=self.username,
                                             password=self.password)
        self.student_name = 'astudent'
        self.student_password = 'blahblah'
        self.student = User.objects.create_user(username=self.student_name,
                                                password=self.student_password)
        self.req = create_test_request(self.user)
        gutils.activate_managers(self.req)

    def tearDown(self):
        envoy.run('mongo test_producer_assessment --eval "db.dropDatabase()"')
        envoy.run('mongo test_producer_grading --eval "db.dropDatabase()"')
        envoy.run('mongo test_producer_repository --eval "db.dropDatabase()"')

    def updated(self, _req):
        self.code(_req, 202)

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
            'learningProviderImpl': {
                'syntax': 'STRING',
                'displayName': 'Learning Provider Implementation',
                'description': 'Implementation for learning service provider',
                'values': [
                    {'value': 'HANDCAR_MC3_DEV', 'priority': 1}
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
            'recordsRegistry': {
                'syntax': 'STRING',
                'displayName': 'Python path to the extension records registry file',
                'description': 'dot-separated path to the extension records registry file',
                'values': [
                    {'value': 'records.registry', 'priority': 1}
                ]
            }
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
