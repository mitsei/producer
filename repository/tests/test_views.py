import os
import boto
import json
import envoy
import requests

from minimocktest import MockTestCase
from django.test.utils import override_settings
from django.utils.http import unquote
from rest_framework.test import APITestCase, APIClient

from assessments_users.models import APIUser

from copy import deepcopy

from utilities import general as gutils
from utilities import repository as rutils
from utilities.testing import configure_test_bucket, create_test_request, create_test_bank

from django.conf import settings

from dlkit_django.primordium import Id, DataInputStream, Type
from dlkit.mongo.records.types import COMPOSITION_RECORD_TYPES, EDX_COMPOSITION_GENUS_TYPES

from boto.s3.key import Key


@override_settings(DLKIT_MONGO_DB_PREFIX='test_',
                   CLOUDFRONT_DISTRO='d1v4o60a4yrgi8.cloudfront.net',
                   CLOUDFRONT_DISTRO_ID='E1OEKZHRUO35M9',
                   S3_BUCKET='mitodl-repository-test')
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

    def create_new_repo(self):
        payload = {
            'name': 'my new repository',
            'description': 'for testing with'
        }
        req = self.new_repo_post(payload)
        return self.json(req)

    def created(self, _req):
        self.code(_req, 201)

    def deleted(self, _req):
        self.code(_req, 204)

    def filename(self, file_):
        try:
            return file_.name.split('/')[-1].split('.')[0]
        except AttributeError:
            return file_.split('/')[-1].split('.')[0]

    def get_repo(self, repo_id):
        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        return rm.get_repository(Id(repo_id))

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

    def new_repo_post(self, payload):
        url = self.url + 'repositories/'
        self.login()
        return self.client.post(url, payload)

    def ok(self, _req):
        self.assertEqual(_req.status_code, 200)

    def setUp(self):
        configure_test_bucket()
        self.url = '/api/v2/repository/'
        self.username = 'cjshaw@mit.edu'
        self.password = 'jinxem'
        self.user = APIUser.objects.create_user(username=self.username,
                                                password=self.password)
        self.student_name = 'astudent'
        self.student_password = 'blahblah'
        self.student = APIUser.objects.create_user(username=self.student_name,
                                                   password=self.student_password)
        self.req = create_test_request(self.user)
        envoy.run('mongo test_repository --eval "db.dropDatabase()"')

    def setup_asset(self, repository_id):
        project_path = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.abspath(os.path.join(project_path, os.pardir))
        test_file = '/tests/files/Flexure_structure_with_hints.pdf'

        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(repository_id))
        asset_form = repo.get_asset_form_for_create([])
        asset_form.display_name = 'test'
        asset_form.description = 'ing'
        new_asset = repo.create_asset(asset_form)

        # now add the new data
        asset_content_type_list = []
        try:
            config = repo._runtime.get_configuration()
            parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
            asset_content_type_list.append(
                config.get_value_by_parameter(parameter_id).get_type_value())
        except AttributeError:
            pass

        asset_content_form = repo.get_asset_content_form_for_create(new_asset.ident,
                                                                    asset_content_type_list)

        self.default_asset_file = abs_path + test_file
        with open(self.default_asset_file, 'r') as file_:
            asset_content_form.set_data(DataInputStream(file_))

        repo.create_asset_content(asset_content_form)

        new_asset = repo.get_asset(new_asset.ident)
        return new_asset.object_map

    def setup_composition(self, repository_id):
        project_path = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.abspath(os.path.join(project_path, os.pardir))
        test_file = '/tests/files/Flexure_structure_with_hints.pdf'

        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(repository_id))
        asset_form = repo.get_asset_form_for_create([])
        asset_form.display_name = 'test'
        asset_form.description = 'ing'
        new_asset = repo.create_asset(asset_form)

        # now add the new data
        asset_content_type_list = []
        try:
            config = repo._runtime.get_configuration()
            parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
            asset_content_type_list.append(
                config.get_value_by_parameter(parameter_id).get_type_value())
        except AttributeError:
            pass

        asset_content_form = repo.get_asset_content_form_for_create(new_asset.ident,
                                                                    asset_content_type_list)

        self.default_asset_file = abs_path + test_file
        with open(self.default_asset_file, 'r') as file_:
            asset_content_form.set_data(DataInputStream(file_))

        repo.create_asset_content(asset_content_form)

        form = repo.get_composition_form_for_create([])
        form.display_name = 'my test composition'
        form.description = 'foobar'
        form.set_children([new_asset.ident])
        composition = repo.create_composition(form)
        return composition.object_map

    def tearDown(self):
        envoy.run('mongo test_repository --eval "db.dropDatabase()"')

    def updated(self, _req):
        self.code(_req, 202)


class AssetCrUDTests(DjangoTestCase):
    """Test the views for repository crud

    """
    def get_asset(self, asset_id):
        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(self.repo['id']))
        return repo.get_asset(Id(asset_id))

    def s3_file_exists(self, key):
        connection = boto.connect_s3(settings.S3_TEST_PUBLIC_KEY,
                                     settings.S3_TEST_PRIVATE_KEY)
        bucket = connection.create_bucket(settings.S3_BUCKET)
        file = Key(bucket, key)
        return file.exists()

    def setUp(self):
        super(AssetCrUDTests, self).setUp()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.repo = self.create_new_repo()

        project_path = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.abspath(os.path.join(project_path, os.pardir))
        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(abs_path + test_file, 'r')
        self.test_file2 = open(abs_path + test_file2, 'r')

    def tearDown(self):
        super(AssetCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_repository_assets(self):
        self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/'
        req = self.client.get(url)
        self.ok(req)
        assets = self.json(req)['data']['results']
        self.assertEqual(
            len(assets),
            1
        )
        asset_contents = assets[0]['assetContents']
        deprecated_asset_contents = assets[0]['assetContent']

        self.assertEqual(
            len(asset_contents),
            1
        )

        self.assertEqual(
            asset_contents,
            deprecated_asset_contents
        )

        self.is_cloudfront_url(asset_contents[0]['url'])

    def test_student_can_view_assets(self):
        self.setup_asset(self.repo['id'])
        self.login(non_instructor=True)
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/'
        req = self.client.get(url)
        self.ok(req)

    def test_can_upload_single_asset(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/'
        payload = {
            'my_asset_label': self.test_file
        }
        req = self.client.post(url, payload)
        self.created(req)
        data = self.json(req)
        self.assertEqual(
            data.keys()[0],
            payload.keys()[0]
        )
        self.assertEqual(
            len(data.keys()),
            1
        )
        asset_id = data[data.keys()[0]]
        self.assertIn(
            'repository.Asset%3A',
            asset_id
        )

        expected_filename = self.filename(self.test_file)
        asset_map = self.get_asset(asset_id).object_map

        self.assertEqual(
            asset_map['displayName']['text'],
            payload.keys()[0]
        )

        self.assertEqual(
            len(asset_map['assetContents']),
            1
        )

        asset_content = asset_map['assetContents'][0]

        # this will be the original S3 URL
        self.assertIn(
            expected_filename,
            asset_content['url']
        )

    def test_can_upload_multiple_assets_simultaneously(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/'
        payload = {
            'my_asset_label': self.test_file,
            'my_second_asset': self.test_file2
        }
        req = self.client.post(url, payload)
        self.created(req)
        data = self.json(req)

        self.assertEqual(
            len(data.keys()),
            2
        )

        expected_keys = payload.keys()

        for asset in data.items():
            label = asset[0]
            self.assertIn(
                label,
                expected_keys
            )
            expected_keys = [key for key in expected_keys if key != label]

            asset_id = asset[1]
            self.assertIn(
                'repository.Asset%3A',
                asset_id
            )

            expected_filename = self.filename(payload[label])
            asset_map = self.get_asset(asset_id).object_map

            self.assertEqual(
                asset_map['displayName']['text'],
                label
            )

            self.assertEqual(
                len(asset_map['assetContents']),
                1
            )

            asset_content = asset_map['assetContents'][0]

            # this will be the original S3 URL
            self.assertIn(
                expected_filename,
                asset_content['url']
            )

    def test_can_get_single_asset_details(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']
        req = self.client.get(url)
        self.ok(req)
        asset_map = self.json(req)
        self.assertEqual(
            asset['id'],
            asset_map['id']
        )
        self.assertEqual(
            asset['displayName']['text'],
            asset_map['displayName']['text']
        )

        self.is_cloudfront_url(asset_map['assetContents'][0]['url'])

        expected_name = self.filename(self.default_asset_file)

        self.assertIn(
            expected_name,
            asset_map['assetContents'][0]['url']
        )

    def test_can_delete_asset(self):
        """Also check that the asset content is removed from AWS"""
        def get_s3_path(url):
            return url.split('amazonaws.com')[-1]

        asset = self.setup_asset(self.repo['id'])
        s3_url = asset['assetContents'][0]['url']
        s3_path = get_s3_path(s3_url)
        self.assertTrue(self.s3_file_exists(s3_path))

        self.login()

        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']
        req = self.client.delete(url)
        self.deleted(req)

        self.assertFalse(self.s3_file_exists(s3_path))

    def test_can_update_asset_name(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'name': 'name v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_asset = self.json(req)
        self.assertEqual(
            updated_asset.keys()[0],
            payload['name']
        )
        self.assertEqual(
            len(updated_asset.keys()),
            1
        )
        updated_asset_obj = self.get_asset(updated_asset[payload['name']])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            payload['name']
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset['description']['text']
        )

        self.assertEqual(
            updated_asset_obj.object_map['assetContents'],
            asset['assetContents']
        )

    def test_can_update_asset_description(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'description': 'desc v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset['displayName']['text']
        self.assertEqual(
            updated_asset.keys()[0],
            asset_name
        )
        self.assertEqual(
            len(updated_asset.keys()),
            1
        )
        updated_asset_obj = self.get_asset(updated_asset[asset_name])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset['displayName']['text']
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            payload['description']
        )

        self.assertEqual(
            updated_asset_obj.object_map['assetContents'],
            asset['assetContents']
        )

    def test_can_update_asset_file_with_single_file(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'file2': self.test_file
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset['displayName']['text']
        self.assertEqual(
            updated_asset.keys()[0],
            asset_name
        )
        self.assertEqual(
            len(updated_asset.keys()),
            1
        )
        updated_asset_obj = self.get_asset(updated_asset[asset_name])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset['displayName']['text']
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset['description']['text']
        )

        updated_ac_map = updated_asset_obj.object_map['assetContents']

        self.assertNotEqual(
            updated_ac_map,
            asset['assetContents']
        )

        self.assertEqual(
            len(updated_ac_map),
            1
        )

        expected_name = self.filename(self.test_file)
        self.assertIn(
            expected_name,
            updated_ac_map[0]['url']
        )

    def test_when_updating_asset_file_previous_contents_deleted(self):
        asset = self.setup_asset(self.repo['id'])
        original_s3_url = asset['assetContents'][0]['url']
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'file2': self.test_file
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset['displayName']['text']
        self.assertEqual(
            updated_asset.keys()[0],
            asset_name
        )
        self.assertEqual(
            len(updated_asset.keys()),
            1
        )
        updated_asset_obj = self.get_asset(updated_asset[asset_name])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset['displayName']['text']
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset['description']['text']
        )

        updated_ac_map = updated_asset_obj.object_map['assetContents']

        self.assertNotEqual(
            updated_ac_map,
            asset['assetContents']
        )

        self.assertEqual(
            len(updated_ac_map),
            1
        )

        unexpected_name = self.filename(self.default_asset_file)
        self.assertNotIn(
            unexpected_name,
            updated_ac_map[0]['url']
        )
        self.assertFalse(self.s3_file_exists(original_s3_url.split('.com')[1]))

    def test_can_update_asset_file_with_multiple_files(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'file2': self.test_file,
            'file3': self.test_file2
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset['displayName']['text']
        self.assertEqual(
            updated_asset.keys()[0],
            asset_name
        )
        self.assertEqual(
            len(updated_asset.keys()),
            1
        )
        updated_asset_obj = self.get_asset(updated_asset[asset_name])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset['displayName']['text']
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset['description']['text']
        )

        updated_ac_map = updated_asset_obj.object_map['assetContents']

        self.assertNotEqual(
            updated_ac_map,
            asset['assetContents']
        )

        self.assertEqual(
            len(updated_ac_map),
            2
        )

        expected_names = [self.filename(self.test_file),
                          self.filename(self.test_file2)]

        for content in updated_ac_map:
            self.assertTrue(any(name in content['url'] for name in expected_names))

            expected_names = [name for name in expected_names if name not in content['url']]

    def test_update_with_no_parameters_throws_exception(self):
        asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + asset['id']

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"name\\", \\"description\\", \\"files\\"')


class BasicServiceTests(DjangoTestCase):
    """Test the views for getting the basic service calls

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_authenticated_users_can_see_available_services(self):
        self.login()
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'documentation')
        self.message(req, 'repositories')

    def test_non_authenticated_users_cannot_see_available_services(self):
        url = self.url
        req = self.client.get(url)
        self.code(req, 403)

    def test_instructors_can_get_list_of_repositories(self):
        self.login()
        url = self.url + 'repositories/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 0')

    def test_learners_can_see_list_of_repositories(self):
        self.login(non_instructor=True)
        url = self.url + 'repositories/'
        req = self.client.get(url)
        self.ok(req)


class CompositionCrUDTests(DjangoTestCase):
    """Test the views for composition crud

    """
    def attach_ids_to_composition(self, composition_id, id_list):
        repo = self.get_repo(self.repo['id'])
        for id_ in id_list:
            repo.add_asset(Id(id_), Id(composition_id))

    def create_bank_with_item_and_assessment(self):
        from utilities import assessment as autils
        autils.activate_managers(self.req)
        am = gutils.get_session_data(self.req, 'am')
        form = am.get_bank_form_for_create([])
        form.display_name = 'Assessment Bank'
        form.description = 'for testing'
        bank = am.create_bank(form)

        form = bank.get_item_form_for_create([])
        form.display_name = 'an item'
        form.description = 'for testing'
        item = bank.create_item(form)

        form = bank.get_assessment_form_for_create([])
        form.display_name = 'an assessment'
        form.description = 'for testing'
        assessment = bank.create_assessment(form)

        bank.add_item(assessment.ident, item.ident)
        assessment = bank.get_assessment(assessment.ident)
        return bank, item, assessment

    def get_asset(self, asset_id):
        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(self.repo['id']))
        return repo.get_asset(Id(asset_id))

    def num_assets(self, val):
        self.assertEqual(
            self.get_repo(self.repo['id']).get_assets().available(),
            val
        )

    def num_compositions(self, val):
        self.assertEqual(
            self.get_repo(self.repo['id']).get_compositions().available(),
            val
        )

    def s3_file_exists(self, key):
        connection = boto.connect_s3(settings.S3_TEST_PUBLIC_KEY,
                                     settings.S3_TEST_PRIVATE_KEY)
        bucket = connection.create_bucket(settings.S3_BUCKET)
        file = Key(bucket, key)
        return file.exists()

    def setUp(self):
        super(CompositionCrUDTests, self).setUp()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.repo = self.create_new_repo()

        project_path = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.abspath(os.path.join(project_path, os.pardir))
        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(abs_path + test_file, 'r')
        self.test_file2 = open(abs_path + test_file2, 'r')

    def tearDown(self):
        super(CompositionCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_repository_compositions(self):
        self.setup_composition(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'
        req = self.client.get(url)
        self.ok(req)
        compositions = self.json(req)['data']['results']
        self.assertEqual(
            len(compositions),
            1
        )

    def test_can_create_composition_without_children(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing'
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_create_composition_with_single_nonlist_child_id(self):
        new_asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'childIds': new_asset['id']
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            new_asset['id'],
            composition['childIds'][0]
        )
        self.assertEqual(
            len(composition['childIds']),
            1
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_can_create_composition_with_asset_child_id_in_list(self):
        new_asset = self.setup_asset(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'childIds': [new_asset['id']]
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            new_asset['id'],
            composition['childIds'][0]
        )
        self.assertEqual(
            len(composition['childIds']),
            1
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_missing_parameters_in_create_throw_exceptions(self):
        self.login()
        self.num_compositions(0)
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing'
        }

        for key in payload.keys():
            mod_payload = deepcopy(payload)
            del mod_payload[key]

            req = self.client.post(url, mod_payload, format='json')
            self.code(req, 500)
            self.num_compositions(0)

    def test_bad_id_in_delete_throws_exception(self):
        self.num_compositions(0)
        self.setup_composition(self.repo['id'])
        self.login()
        self.num_compositions(1)

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/123foo'
        req = self.client.delete(url)
        self.code(req, 500)
        self.num_compositions(1)

    def test_can_delete_composition(self):
        self.num_compositions(0)
        composition = self.setup_composition(self.repo['id'])
        self.login()
        self.num_compositions(1)

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']
        req = self.client.delete(url)
        self.deleted(req)
        self.num_compositions(0)

    def test_can_get_composition_details(self):
        new_composition = self.setup_composition(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + new_composition['id']

        req = self.client.get(url)
        self.ok(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            1
        )
        self.assertEqual(
            composition['displayName']['text'],
            new_composition['displayName']['text']
        )
        self.assertEqual(
            composition['description']['text'],
            new_composition['description']['text']
        )
        self.assertIn(
            '_links',
            composition
        )

    def test_can_update_composition_attributes(self):
        composition = self.setup_composition(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']

        test_cases = [{'name': 'ha'},
                      {'description': 'funny'}]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)
            if payload.keys()[0] == 'name':
                self.assertEqual(
                    data['displayName']['text'],
                    payload['name']
                )
            else:
                self.assertEqual(
                    data['description']['text'],
                    payload['description']
                )

    def test_updating_child_ids_removes_previous_ones(self):
        composition = self.setup_composition(self.repo['id'])
        self.num_compositions(1)
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']

        # get the original asset id
        req = self.client.get(url)
        data = self.json(req)
        old_asset_id = data['childIds'][0]

        new_asset = self.setup_asset(self.repo['id'])

        payload = {
            'childIds': new_asset['id']
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            new_asset['id']
        )
        self.assertEqual(
            data['childIds'],
            [new_asset['id']]
        )
        self.num_compositions(1)

    def test_updating_child_ids_preserves_order(self):
        composition = self.setup_composition(self.repo['id'])
        self.num_compositions(1)
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']

        # get the original asset id
        req = self.client.get(url)
        data = self.json(req)
        old_asset_id = data['childIds'][0]

        new_asset = self.setup_asset(self.repo['id'])

        payload = {
            'childIds': [old_asset_id, new_asset['id']]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            new_asset['id']
        )
        self.assertEqual(
            data['childIds'],
            [old_asset_id, new_asset['id']]
        )
        self.num_compositions(1)

        payload = {
            'childIds': [new_asset['id'], old_asset_id]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            new_asset['id']
        )
        self.assertEqual(
            data['childIds'],
            [new_asset['id'], old_asset_id]
        )
        self.num_compositions(1)

    def test_update_with_no_parameters_throws_exception(self):
        new_composition = self.setup_composition(self.repo['id'])
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + new_composition['id']

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"name\\", \\"description\\", \\"childIds\\"')

    def test_can_get_composition_assets(self):
        asset = self.setup_asset(self.repo['id'])
        composition = self.setup_composition(self.repo['id'])
        self.attach_ids_to_composition(composition['id'], [asset['id']])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        assets = data['data']['results']
        self.assertEqual(
            assets[0]['id'],
            asset['id']
        )
        self.assertEqual(
            assets[0]['displayName']['text'],
            asset['displayName']['text']
        )

        self.assertEqual(
            assets[0]['description']['text'],
            asset['description']['text']
        )

    def test_asset_urls_point_to_root_asset_details(self):
        asset = self.setup_asset(self.repo['id'])
        composition = self.setup_composition(self.repo['id'])
        self.attach_ids_to_composition(composition['id'], [asset['id']])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        asset_url = data['data']['results'][0]['_link']
        self.assertIn(
            unquote('repositories/' + self.repo['id'] + '/compositions/' + composition['id'] +
                    '/assets/../../../assets/' + asset['id'] + '/'),
            asset_url
        )

    def test_can_get_compositions_enclosed_assets(self):
        self.num_assets(0)

        bank, item, assessment = self.create_bank_with_item_and_assessment()
        composition = self.setup_composition(self.repo['id'])
        self.num_assets(1)

        self.attach_ids_to_composition(composition['id'], [str(assessment.ident)])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        assets = data['data']['results']
        self.assertEqual(
            assets[0]['enclosedObjectId'],
            str(assessment.ident)
        )
        self.assertNotEqual(
            Id(assets[0]['id']).identifier,
            assessment.ident.identifier
        )

        self.assertEqual(
            assets[0]['displayName']['text'],
            assessment.display_name.text
        )

        self.assertEqual(
            assets[0]['description']['text'],
            assessment.description.text
        )

        self.assertEqual(
            assets[0]['genusTypeId'],
            'assessment%3AAssessment%40osid.org'
        )

        self.num_assets(2)

    def test_can_attach_one_asset_to_composition(self):
        composition = self.setup_composition(self.repo['id'])
        asset = self.setup_asset(self.repo['id'])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': asset['id']
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )

        assets = data['data']['results']

        self.assertEqual(
            assets[0]['id'],
            asset['id']
        )

    def test_can_attach_one_non_asset_to_composition(self):
        composition = self.setup_composition(self.repo['id'])
        bank, item, assessment = self.create_bank_with_item_and_assessment()

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': str(assessment.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )

        assets = data['data']['results']

        self.assertEqual(
            assets[0]['enclosedObjectId'],
            str(assessment.ident)
        )

    def test_can_attach_multiple_assets_to_composition(self):
        composition = self.setup_composition(self.repo['id'])
        asset = self.setup_asset(self.repo['id'])
        asset2 = self.setup_asset(self.repo['id'])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': [asset['id'], asset2['id']]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            2
        )

        assets = data['data']['results']

        self.assertEqual(
            assets[0]['id'],
            asset['id']
        )
        self.assertEqual(
            assets[1]['id'],
            asset2['id']
        )

    def test_can_attach_multiple_non_assets_to_composition(self):
        composition = self.setup_composition(self.repo['id'])
        bank, item, assessment = self.create_bank_with_item_and_assessment()
        bank2, item2, assessment2 = self.create_bank_with_item_and_assessment()

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': [str(assessment.ident), str(assessment2.ident)]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            2
        )

        assets = data['data']['results']

        self.assertEqual(
            assets[0]['enclosedObjectId'],
            str(assessment.ident)
        )
        self.assertEqual(
            assets[1]['enclosedObjectId'],
            str(assessment2.ident)
        )

    def test_exception_thrown_if_no_params_passed_to_attach_assets(self):
        self.num_assets(0)

        asset = self.setup_asset(self.repo['id'])
        composition = self.setup_composition(self.repo['id'])
        self.num_assets(2)

        self.attach_ids_to_composition(composition['id'], [asset['id']])

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"assetIds\\" required in input parameters but not provided.')

    def test_cannot_edit_some_enclosed_asset_attributes(self):
        composition = self.setup_composition(self.repo['id'])
        bank, item, assessment = self.create_bank_with_item_and_assessment()

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        payload = {
            'assetIds': str(assessment.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        assets = data['data']['results']

        enclosure_id = assets[0]['id']

        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + enclosure_id + '/'

        payload = {
            'name': 'foo',
            'description': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot edit those fields.')

    def test_can_add_files_to_enclosed_assets(self):
        composition = self.setup_composition(self.repo['id'])
        bank, item, assessment = self.create_bank_with_item_and_assessment()

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id'] + '/assets/'
        self.login()

        payload = {
            'assetIds': str(assessment.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        req = self.client.get(url)
        data = self.json(req)
        assets = data['data']['results']

        enclosure_id = assets[0]['id']

        url = self.url + 'repositories/' + self.repo['id'] + '/assets/' + enclosure_id + '/'

        payload = {
            'testFile': self.test_file
        }

        req = self.client.put(url, payload)
        self.code(req, 202)

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)

        expected = self.filename(self.test_file)
        self.assertIn(
            expected,
            data['assetContents'][0]['url']
        )
        self.is_cloudfront_url(data['assetContents'][0]['url'])


class DocumentationTests(DjangoTestCase):
    """Test the views for getting the documentation

    """
    def setUp(self):
        super(DocumentationTests, self).setUp()

    def tearDown(self):
        super(DocumentationTests, self).tearDown()

    def test_authenticated_users_can_view_docs(self):
        self.login()
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Repository Service, V1')

    def test_non_authenticated_users_can_view_docs(self):
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Repository Service, V1')

    def test_student_can_view_docs(self):
        self.login(non_instructor=True)
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Repository Service, V1')


class EdXCompositionCrUDTests(CompositionCrUDTests):
    """Test the views for composition crud

    """
    def setUp(self):
        super(EdXCompositionCrUDTests, self).setUp()

    def tearDown(self):
        super(EdXCompositionCrUDTests, self).tearDown()

    def test_can_create_edx_composition_with_genus_type(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-course'
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )
        self.assertEqual(
            composition['genusTypeId'],
            str(Type(**EDX_COMPOSITION_GENUS_TYPES['course']))
        )
        self.assertIn(
            str(Type(**COMPOSITION_RECORD_TYPES['edx-composition'])),
            composition['recordTypeIds']
        )

    def test_throw_exception_if_bad_genus_type_provided(self):
        self.login()
        self.num_compositions(0)
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-filly'
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Bad genus type provided.')

        self.num_compositions(0)

    def test_can_set_edx_composition_values_on_create_chapter(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-chapter',
            'startDate': {
                'year': 2015,
                'month': 1,
                'day': 1
            },
            'endDate': {
                'year': 2016,
                'month': 2,
                'day': 1
            },
            'visibleToStudents': False
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )
        self.assertEqual(
            composition['genusTypeId'],
            str(Type(**EDX_COMPOSITION_GENUS_TYPES['chapter']))
        )
        self.assertIn(
            str(Type(**COMPOSITION_RECORD_TYPES['edx-composition'])),
            composition['recordTypeIds']
        )

        self.assertFalse(composition['visibleToStudents'])

        for attr, val in payload['startDate'].iteritems():
            self.assertEqual(
                composition['startDate'][attr],
                val
            )

        for attr, val in payload['endDate'].iteritems():
            self.assertEqual(
                composition['endDate'][attr],
                val
            )

    def test_can_set_edx_composition_values_on_create_vertical(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-vertical',
            'draft': True
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )
        self.assertEqual(
            composition['genusTypeId'],
            str(Type(**EDX_COMPOSITION_GENUS_TYPES['vertical']))
        )
        self.assertIn(
            str(Type(**COMPOSITION_RECORD_TYPES['edx-composition'])),
            composition['recordTypeIds']
        )

        self.assertTrue(composition['draft'])

    def test_can_update_edx_composition_values_chapter(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-chapter',
            'startDate': {
                'year': 2015,
                'month': 1,
                'day': 1
            },
            'endDate': {
                'year': 2016,
                'month': 2,
                'day': 1
            },
            'visibleToStudents': False
        }

        req = self.client.post(url, payload, format='json')
        composition = self.json(req)

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']

        payload2 = {
            'startDate': {
                'year': 2015,
                'month': 5,
                'day': 10
            },
            'endDate': {
                'year': 2016,
                'month': 12,
                'day': 12
            },
            'visibleToStudents': True
        }

        req = self.client.put(url, payload2, format='json')
        self.updated(req)
        composition2 = self.json(req)

        self.assertTrue(composition2['visibleToStudents'])

        for attr, val in payload2['startDate'].iteritems():
            self.assertEqual(
                composition2['startDate'][attr],
                val
            )

        for attr, val in payload2['endDate'].iteritems():
            self.assertEqual(
                composition2['endDate'][attr],
                val
            )

    def test_can_update_edx_composition_values_vertical(self):
        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing',
            'type': 'edx-vertical',
            'draft': True
        }

        req = self.client.post(url, payload, format='json')
        composition = self.json(req)

        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/' + composition['id']

        payload2 = {
            'draft': False
        }

        req = self.client.put(url, payload2, format='json')
        self.updated(req)
        composition2 = self.json(req)

        self.assertFalse(composition2['draft'])

    def test_can_query_compositions_by_type(self):
        self.num_compositions(0)
        self.setup_composition(self.repo['id'])
        self.num_compositions(1)

        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing querying',
            'type': 'edx-chapter',
            'startDate': {
                'year': 2015,
                'month': 1,
                'day': 1
            },
            'endDate': {
                'year': 2016,
                'month': 2,
                'day': 1
            },
            'visibleToStudents': False
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        new_comp = self.json(req)

        self.num_compositions(2)

        url += '?chapter'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            1
        )
        comp = data['data']['results'][0]
        self.assertEqual(
            comp['id'],
            new_comp['id']
        )
        self.assertEqual(
            comp['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            comp['description']['text'],
            payload['description']
        )

    def test_bad_query_type_throws_exception(self):
        self.num_compositions(0)
        self.setup_composition(self.repo['id'])
        self.num_compositions(1)

        self.login()
        url = self.url + 'repositories/' + self.repo['id'] + '/compositions/'

        payload = {
            'name': 'test composition',
            'description': 'for testing querying',
            'type': 'edx-chapter',
            'startDate': {
                'year': 2015,
                'month': 1,
                'day': 1
            },
            'endDate': {
                'year': 2016,
                'month': 2,
                'day': 1
            },
            'visibleToStudents': False
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        new_comp = self.json(req)

        self.num_compositions(2)

        url += '?chapter&foo'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req,
                     'Invalid query genus type provided. Only \\"course\\", ' +
                     '\\"chapter\\", \\"sequential\\", \\"split_test\\", and \\"vertical\\" ' +
                     'are allowed.')

class RepositoryCrUDTests(DjangoTestCase):
    """Test the views for repository crud

    """
    def num_repos(self, val):
        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')

        self.assertEqual(
            rm.repositories.available(),
            val
        )

    def setUp(self):
        super(RepositoryCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.assessment_bank = create_test_bank(self)
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'

    def tearDown(self):
        envoy.run('mongo test_assessment --eval "db.dropDatabase()"')
        super(RepositoryCrUDTests, self).tearDown()

    def test_can_create_new_repository(self):
        payload = {
            'name': 'my new repository',
            'description': 'for testing with'
        }
        req = self.new_repo_post(payload)
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            repo['description']['text'],
            payload['description']
        )

    def test_can_create_orchestrated_repository_with_default_attributes(self):
        url = self.url + 'repositories/'
        payload = {
            'bankId': self.assessment_bank['id']
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            'Orchestrated assessment Repository'
        )
        self.assertEqual(
            repo['description']['text'],
            'Orchestrated Repository for the assessment service'
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(repo['id']).identifier
        )

    def test_can_create_orchestrated_repository_and_set_attributes(self):
        url = self.url + 'repositories/'
        payload = {
            'bankId': self.assessment_bank['id'],
            'name': 'my new orchestra',
            'description': 'for my assessment bank'
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            repo['description']['text'],
            payload['description']
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(repo['id']).identifier
        )

    def test_missing_parameters_throws_exception_on_create(self):
        self.num_repos(0)

        url = self.url + 'repositories/'
        basic_payload = {
            'name': 'my new repository',
            'description': 'for testing with'
        }
        blacklist = ['name', 'description']
        self.login()

        for item in blacklist:
            payload = deepcopy(basic_payload)
            del payload[item]
            req = self.client.post(url, payload)
            self.code(req, 500)
            self.message(req,
                         '\\"' + item + '\\" required in input parameters but not provided.')

        self.num_repos(0)

    def test_can_get_repository_details(self):
        self.login()
        repo = self.create_new_repo()
        url = self.url + 'repositories/' + str(repo['id'])
        req = self.client.get(url)
        self.ok(req)
        repo_details = self.json(req)
        for attr, val in repo.iteritems():
            self.assertEqual(
                val,
                repo_details[attr]
            )
        self.message(req, '"assets":')

    def test_invalid_repository_id_throws_exception(self):
        self.login()
        self.create_new_repo()
        url = self.url + 'repositories/x'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Invalid ID.')

    def test_bad_repository_id_throws_exception(self):
        self.login()
        self.create_new_repo()
        url = self.url + 'repositories/' + self.bad_repo_id
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

    def test_can_delete_repository(self):
        self.num_repos(0)

        self.login()

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + 'repositories/' + str(repo['id'])
        req = self.client.delete(url)
        self.deleted(req)

        self.num_repos(0)

    def test_trying_to_delete_repository_with_assets_throws_exception(self):
        self.num_repos(0)

        self.login()

        repo = self.create_new_repo()

        self.num_repos(1)
        self.setup_asset(repo['id'])

        url = self.url + 'repositories/' + str(repo['id'])
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Repository is not empty.')

        self.num_repos(1)

    def test_trying_to_delete_repository_with_invalid_id_throws_exception(self):
        self.num_repos(0)

        self.login()

        self.create_new_repo()

        self.num_repos(1)

        url = self.url + 'repositories/' + self.bad_repo_id
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

        self.num_repos(1)

    def test_can_update_repository(self):
        self.num_repos(0)

        self.login()

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + 'repositories/' + str(repo['id'])

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            updated_repo = self.json(req)
            if case[0] == 'name':
                self.assertEqual(
                    updated_repo['displayName']['text'],
                    case[1]
                )
            else:
                self.assertEqual(
                    updated_repo['description']['text'],
                    case[1]
                )

        self.num_repos(1)

    def test_update_with_invalid_id_throws_exception(self):
        self.num_repos(0)

        self.login()

        self.create_new_repo()

        self.num_repos(1)

        url = self.url + 'repositories/' + self.bad_repo_id

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req, 'Object not found.')

        self.num_repos(1)

    def test_update_with_no_params_throws_exception(self):
        self.num_repos(0)

        self.login()

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + 'repositories/' + str(repo['id'])

        test_cases = [('foo', 'bar'),
                      ('bankId', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req,
                         'At least one of the following must be passed in: ' +
                         '[\\"name\\", \\"description\\"]')

        self.num_repos(1)
        req = self.client.get(url)
        repo_fresh = self.json(req)

        params_to_test = ['id', 'displayName', 'description']
        for param in params_to_test:
            self.assertEqual(
                repo[param],
                repo_fresh[param]
            )

    def test_student_can_view_repositories(self):
        self.create_new_repo()
        self.login(non_instructor=True)
        self.num_repos(1)

        url = self.url + 'repositories/'
        req = self.client.get(url)
        self.ok(req)
