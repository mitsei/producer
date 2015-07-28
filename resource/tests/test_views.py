import os
import boto
import json
import envoy

from minimocktest import MockTestCase
from django.test.utils import override_settings
from rest_framework.test import APITestCase, APIClient

from assessments_users.models import APIUser

from copy import deepcopy

from utilities import general as gutils
from utilities import repository as rutils
from utilities import resource as resutils
from utilities.testing import configure_test_bucket, create_test_request, create_test_bank

from django.conf import settings

from dlkit_django.primordium import Id, DataInputStream

from boto.s3.key import Key


PROJECT_PATH = os.path.dirname(os.path.abspath(__file__))
ABS_PATH = os.path.abspath(os.path.join(PROJECT_PATH, os.pardir))


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

    def create_new_bin(self):
        payload = {
            'name': 'my new bin',
            'description': 'for testing with'
        }
        req = self.new_bin_post(payload)
        return self.json(req)

    def created(self, _req):
        self.code(_req, 201)

    def deleted(self, _req):
        self.code(_req, 204)

    def filename(self, file_):
        try:
            return file_.name.split('/')[-1]
        except AttributeError:
            return file_.split('/')[-1]

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

    def new_bin_post(self, payload):
        url = self.url + 'bins/'
        self.login()
        return self.client.post(url, payload)

    def ok(self, _req):
        self.assertEqual(_req.status_code, 200)

    def setUp(self):
        configure_test_bucket()
        self.url = '/api/v2/resource/'
        self.username = 'cjshaw@mit.edu'
        self.password = 'jinxem'
        self.user = APIUser.objects.create_user(username=self.username,
                                                password=self.password)
        self.student_name = 'astudent'
        self.student_password = 'blahblah'
        self.student = APIUser.objects.create_user(username=self.student_name,
                                                   password=self.student_password)
        self.req = create_test_request(self.user)

        self.test_file = open(ABS_PATH + '/tests/files/Flexure_structure_with_hints.pdf')

        envoy.run('mongo test_resource --eval "db.dropDatabase()"')

    def setup_resource(self, bin_id):
        resutils.activate_managers(self.req)
        resm = gutils.get_session_data(self.req, 'resm')
        rm = gutils.get_session_data(self.req, 'rm')

        bin_ = resm.get_bin(Id(bin_id))
        repo = rm.get_repository(Id(bin_id))  # orchestrated

        avatar_label, avatar_id = rutils.create_asset(repo, ('avatar', self.test_file))

        resource_form = bin_.get_resource_form_for_create([])
        resource_form.display_name = 'test ing'
        resource_form.description = 'foo'

        resource_form.set_avatar(Id(avatar_id))

        new_resource = bin_.create_resource(resource_form)

        # assign the agent to a resource
        bin_.assign_agent_to_resource(bin_.effective_agent_id, new_resource.ident)

        return new_resource.object_map

    def tearDown(self):
        self.test_file.close()
        envoy.run('mongo test_resource --eval "db.dropDatabase()"')

    def updated(self, _req):
        self.code(_req, 202)


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
        self.message(req, 'bins')

    def test_non_authenticated_users_cannot_see_available_services(self):
        url = self.url
        req = self.client.get(url)
        self.code(req, 403)

    def test_instructors_can_get_list_of_bins(self):
        self.login()
        url = self.url + 'bins/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 0')

    def test_learners_can_see_list_of_bins(self):
        self.login(non_instructor=True)
        url = self.url + 'bins/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 0')



class BinCrUDTests(DjangoTestCase):
    """Test the views for bin crud

    """
    def num_bins(self, val):
        resutils.activate_managers(self.req)
        resm = gutils.get_session_data(self.req, 'resm')

        self.assertEqual(
            resm.bins.available(),
            val
        )

    def setUp(self):
        super(BinCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.assessment_bank = create_test_bank(self)
        self.bad_bin_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'

    def tearDown(self):
        super(BinCrUDTests, self).tearDown()

    def test_can_create_new_bin(self):
        payload = {
            'name': 'my new bin',
            'description': 'for testing with'
        }
        req = self.new_bin_post(payload)
        self.created(req)
        bin_ = self.json(req)
        self.assertEqual(
            bin_['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            bin_['description']['text'],
            payload['description']
        )


    def test_can_create_orchestrated_bin_with_default_attributes(self):
        url = self.url + 'bins/'
        payload = {
            'bankId': self.assessment_bank['id']
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        bin_ = self.json(req)
        self.assertEqual(
            bin_['displayName']['text'],
            'Orchestrated assessment Bin'
        )
        self.assertEqual(
            bin_['description']['text'],
            'Orchestrated Bin for the assessment service'
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(bin_['id']).identifier
        )


    def test_can_create_orchestrated_bin_and_set_attributes(self):
        url = self.url + 'bins/'
        payload = {
            'bankId': self.assessment_bank['id'],
            'name': 'my new orchestra',
            'description': 'for my assessment bank'
        }
        self.login()
        req = self.client.post(url, payload)
        self.created(req)
        bin_ = self.json(req)
        self.assertEqual(
            bin_['displayName']['text'],
            payload['name']
        )
        self.assertEqual(
            bin_['description']['text'],
            payload['description']
        )
        self.assertEqual(
            Id(self.assessment_bank['id']).identifier,
            Id(bin_['id']).identifier
        )


    def test_missing_parameters_throws_exception_on_create(self):
        self.num_bins(0)

        url = self.url + 'bins/'
        basic_payload = {
            'name': 'my new bin',
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

        self.num_bins(0)

    def test_can_get_bin_details(self):
        self.login()
        bin_ = self.create_new_bin()
        url = self.url + 'bins/' + str(bin_['id'])
        req = self.client.get(url)
        self.ok(req)
        bin_details = self.json(req)
        for attr, val in bin_.iteritems():
            self.assertEqual(
                val,
                bin_details[attr]
            )
        self.message(req, '"resources":')


    def test_invalid_bin_id_throws_exception(self):
        self.login()
        self.create_new_bin()
        url = self.url + 'bins/x'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Invalid ID.')


    def test_bad_bin_id_throws_exception(self):
        self.login()
        self.create_new_bin()
        url = self.url + 'bins/' + self.bad_bin_id
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

    def test_can_delete_bin(self):
        self.num_bins(0)

        self.login()

        bin_ = self.create_new_bin()

        self.num_bins(1)

        url = self.url + 'bins/' + str(bin_['id'])
        req = self.client.delete(url)
        self.deleted(req)

        self.num_bins(0)

    def test_trying_to_delete_bin_with_resources_throws_exception(self):
        self.num_bins(0)

        self.login()

        bin_ = self.create_new_bin()

        self.num_bins(1)
        self.setup_resource(bin_['id'])

        url = self.url + 'bins/' + str(bin_['id'])
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Bin is not empty.')

        self.num_bins(1)


    def test_trying_to_delete_bin_with_invalid_id_throws_exception(self):
        self.num_bins(0)

        self.login()

        self.create_new_bin()

        self.num_bins(1)

        url = self.url + 'bins/' + self.bad_bin_id
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

        self.num_bins(1)


    def test_can_update_bin(self):
        self.num_bins(0)

        self.login()

        bin_ = self.create_new_bin()

        self.num_bins(1)

        url = self.url + 'bins/' + str(bin_['id'])

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            updated_bin = self.json(req)
            if case[0] == 'name':
                self.assertEqual(
                    updated_bin['displayName']['text'],
                    case[1]
                )
            else:
                self.assertEqual(
                    updated_bin['description']['text'],
                    case[1]
                )

        self.num_bins(1)


    def test_update_with_invalid_id_throws_exception(self):
        self.num_bins(0)

        self.login()

        self.create_new_bin()

        self.num_bins(1)

        url = self.url + 'bins/' + self.bad_bin_id

        test_cases = [('name', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.code(req, 500)
            self.message(req, 'Object not found.')

        self.num_bins(1)


    def test_update_with_no_params_throws_exception(self):
        self.num_bins(0)

        self.login()

        bin_ = self.create_new_bin()

        self.num_bins(1)

        url = self.url + 'bins/' + str(bin_['id'])

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

        self.num_bins(1)
        req = self.client.get(url)
        bin_fresh = self.json(req)

        params_to_test = ['id', 'displayName', 'description']
        for param in params_to_test:
            self.assertEqual(
                bin_[param],
                bin_fresh[param]
            )

    def test_student_can_view_bins(self):
        self.create_new_bin()
        self.login(non_instructor=True)
        self.num_bins(1)

        url = self.url + 'bins/'
        req = self.client.get(url)
        self.ok(req)


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
        self.message(req, 'Documentation for MIT Resource Service, V2')


    def test_non_authenticated_users_can_view_docs(self):
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Resource Service, V2')


    def test_student_can_view_docs(self):
        self.login(non_instructor=True)
        url = self.url + 'docs/'
        req = self.client.get(url)
        self.ok(req)
        self.message(req, 'Documentation for MIT Resource Service, V2')


class ResourceCrUDTests(DjangoTestCase):
    """Test the views for resource crud

    """
    def get_asset(self, asset_id):
        rutils.activate_managers(self.req)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(self.repo['id']))
        return repo.get_asset(Id(asset_id))

    def get_resource(self, resource_id):
        rutils.activate_managers(self.req)
        resm = gutils.get_session_data(self.req, 'resm')
        bin_ = resm.get_bin(Id(self.bin['id']))
        return bin_.get_resource(Id(resource_id))

    def get_resource_avatar_url_key(self, resource_id):
        def get_s3_path(url):
            return url.split('amazonaws.com')[-1].split('?')[0]

        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(self.bin['id']))

        resm = gutils.get_session_data(self.req, 'resm')
        bin_ = resm.get_bin(Id(self.bin['id']))
        resource = bin_.get_resource(Id(resource_id))

        avatar_asset = repo.get_asset(resource.get_avatar_id())
        avatar_asset_map = avatar_asset.object_map
        return get_s3_path(avatar_asset_map['assetContents'][0]['url'])

    def num_resources(self, val):
        resutils.activate_managers(self.req)
        resm = gutils.get_session_data(self.req, 'resm')

        bin_ = resm.get_bin(Id(self.bin['id']))
        self.assertEqual(
            bin_.get_resources().available(),
            val
        )

    def s3_file_exists(self, key):
        connection = boto.connect_s3(settings.S3_TEST_PUBLIC_KEY,
                                     settings.S3_TEST_PRIVATE_KEY)
        bucket = connection.create_bucket(settings.S3_BUCKET)
        file = Key(bucket, key)
        return file.exists()

    def setUp(self):
        super(ResourceCrUDTests, self).setUp()
        self.bad_bin_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40bazzim.MIT.EDU'
        self.bin = self.create_new_bin()

        test_file = '/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.student2_name = 'astudent2'
        self.student2_password = 'blahblah'
        self.student2 = APIUser.objects.create_user(username=self.student2_name,
                                                    password=self.student2_password)

    def tearDown(self):
        super(ResourceCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_bin_resources_without_url(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            1
        )
        self.assertEqual(
            resources[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            resources[0]['description']['text'],
            'foo'
        )
        self.assertNotIn(
            'avatarURL',
            resources[0]
        )
        self.assertNotEqual(
            resources[0]['avatarId'],
            ''
        )
        self.s3_file_exists(Id(self.bin['id']).identifier + '/' + self.test_file.name.split('/')[-1])

    def test_can_get_bin_resources_with_urls(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/?avatar_urls'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            1
        )
        self.assertEqual(
            resources[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            resources[0]['description']['text'],
            'foo'
        )
        self.assertIn(
            'avatarURL',
            resources[0]
        )
        self.is_cloudfront_url(resources[0]['avatarURL'])

        self.assertNotEqual(
            resources[0]['avatarId'],
            ''
        )
        self.s3_file_exists(Id(self.bin['id']).identifier + '/' + self.test_file.name.split('/')[-1])

    def test_query_with_no_results(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/?agent=birdland@mit.edu'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            0
        )

    def test_query_bin_resources_with_simple_kerberos(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/?agent=cjshaw'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            1
        )
        self.assertEqual(
            resources[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            resources[0]['description']['text'],
            'foo'
        )
        self.assertNotIn(
            'avatarURL',
            resources[0]
        )

        self.assertNotEqual(
            resources[0]['avatarId'],
            ''
        )
        self.s3_file_exists(Id(self.bin['id']).identifier + '/' + self.test_file.name.split('/')[-1])

    def test_can_query_bin_resources_by_kerberos_and_without_urls(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/?agent=cjshaw@mit.edu'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            1
        )
        self.assertEqual(
            resources[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            resources[0]['description']['text'],
            'foo'
        )
        self.assertNotIn(
            'avatarURL',
            resources[0]
        )

        self.assertNotEqual(
            resources[0]['avatarId'],
            ''
        )
        self.s3_file_exists(Id(self.bin['id']).identifier + '/' + self.test_file.name.split('/')[-1])

    def test_can_query_bin_resources_by_kerberos_and_with_urls(self):
        self.setup_resource(self.bin['id'])
        self.login()
        url = self.url + 'bins/' + self.bin['id'] + '/resources/?agent=cjshaw@mit.edu&avatar_urls'
        req = self.client.get(url)
        self.ok(req)
        resources = self.json(req)['data']['results']
        self.assertEqual(
            len(resources),
            1
        )
        self.assertEqual(
            resources[0]['displayName']['text'],
            'test ing'
        )
        self.assertEqual(
            resources[0]['description']['text'],
            'foo'
        )
        self.assertIn(
            'avatarURL',
            resources[0]
        )
        self.is_cloudfront_url(resources[0]['avatarURL'])

        self.assertNotEqual(
            resources[0]['avatarId'],
            ''
        )
        self.s3_file_exists(Id(self.bin['id']).identifier + '/' + self.test_file.name.split('/')[-1])

    def test_student_can_view_resources(self):
        self.setup_resource(self.bin['id'])
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )

    def test_student_can_view_other_students_resources(self):
        self.req = create_test_request(self.student2)
        stu2_resource = self.setup_resource(self.bin['id'])
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + stu2_resource['id']
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            stu2_resource['id'],
            data['id']
        )
        self.assertIn(
            'avatarURL',
            data
        )
        self.is_cloudfront_url(data['avatarURL'])

    def test_student_can_create_resource(self):
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        payload = {
            'name': self.student_name,
            'description': 'foobar',
            'avatar': self.test_file
        }
        req = self.client.post(url, payload)
        self.created(req)
        data = self.json(req)

        expected_keys = ['binId', 'description', 'displayName',
                         'avatarURL', 'avatarId', 'type', 'id']
        for key in expected_keys:
            self.assertIn(
                key,
                data
            )

        self.is_cloudfront_url(data['avatarURL'])

        expected_filename = self.test_file.name.split('/')[-1].split('.')[0]
        self.assertIn(
            expected_filename,
            data['avatarURL']
        )

    def test_create_throws_exception_if_wrong_file_field_name_specified(self):
        self.num_resources(0)
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        payload = {
            'name': self.student_name,
            'description': 'foobar',
            'fake': self.test_file
        }
        req = self.client.post(url, payload)
        self.code(req, 500)
        self.message(req, 'The avatar file must use the field name \\"avatar\\".')
        self.num_resources(0)

    def test_timestamp_in_resource_avatar_url(self):
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        payload = {
            'name': self.student_name,
            'description': 'foobar',
            'avatar': self.test_file
        }
        req = self.client.post(url, payload)
        self.created(req)
        data = self.json(req)

        expected_filename = self.test_file.name.split('/')[-1]
        extension = expected_filename.split('.')[-1]
        label = expected_filename.split('.')[0]

        avatar_url = data['avatarURL']
        timestamp = avatar_url.split(
            '/')[-1].split('?')[0].replace(
            label + '_', '').replace('.' + extension, '')
        try:
            int(timestamp)
        except ValueError:
            self.fail('Not a valid timestamp.')

    def test_student_cannot_create_resource_if_one_exists_for_them(self):
        self.num_resources(0)
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        payload = {
            'name': self.student_name,
            'description': 'foobar',
            'avatar': self.test_file
        }
        req = self.client.post(url, payload)
        self.created(req)

        self.num_resources(1)

        payload = {
            'name': self.student_name,
            'description': 'foobar',
            'avatar': self.test_file2
        }
        req = self.client.post(url, payload)
        self.code(req, 403)

        self.num_resources(1)

    def test_at_least_one_parameter_needed_on_resource_create(self):
        self.num_resources(0)
        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/'
        payload = {
            'avatar': self.test_file
        }

        req = self.client.post(url, payload)
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"name\\", \\"description\\"]')

        self.num_resources(0)

    def test_student_can_delete_own_resource(self):
        """Also check that the asset content is removed from AWS"""
        self.num_resources(0)

        self.req = create_test_request(self.student)
        resutils.activate_managers(self.req)
        resource_map = self.setup_resource(self.bin['id'])

        s3_path = self.get_resource_avatar_url_key(resource_map['id'])
        self.assertTrue(self.s3_file_exists(s3_path))
        self.num_resources(1)

        self.login(non_instructor=True)

        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource_map['id']
        req = self.client.delete(url)
        self.deleted(req)

        self.assertFalse(self.s3_file_exists(s3_path))
        self.num_resources(0)

    def test_student_cannot_delete_other_students_resources(self):
        self.num_resources(0)

        self.req = create_test_request(self.student2)
        resutils.activate_managers(self.req)
        resource_map = self.setup_resource(self.bin['id'])

        s3_path = self.get_resource_avatar_url_key(resource_map['id'])
        self.assertTrue(self.s3_file_exists(s3_path))
        self.num_resources(1)

        self.req = create_test_request(self.student)
        self.login(non_instructor=True)

        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource_map['id']
        req = self.client.delete(url)
        self.code(req, 403)

        self.assertTrue(self.s3_file_exists(s3_path))
        self.num_resources(1)

    def test_student_can_update_their_own_resource_name(self):
        self.num_resources(0)
        self.req = create_test_request(self.student)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'name': 'name v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_resource = self.json(req)
        self.assertEqual(
            updated_resource['displayName']['text'],
            payload['name']
        )

        self.assertEqual(
            updated_resource['description']['text'],
            resource['description']['text']
        )

        self.assertEqual(
            updated_resource['avatarId'],
            resource['avatarId']
        )

        self.assertIn(
            'avatarURL',
            updated_resource
        )

        self.is_cloudfront_url(updated_resource['avatarURL'])
        self.num_resources(1)

    def test_student_cannot_update_name_of_anothers_resource(self):
        self.num_resources(0)
        self.req = create_test_request(self.student2)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'name': 'name v2'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 403)

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertNotEqual(
            data['displayName']['text'],
            payload['name']
        )

        self.num_resources(1)

    def test_student_can_update_own_resource_description(self):
        self.num_resources(0)
        self.req = create_test_request(self.student)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'description': 'description v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_resource = self.json(req)
        self.assertEqual(
            updated_resource['displayName']['text'],
            resource['displayName']['text']
        )

        self.assertEqual(
            updated_resource['description']['text'],
            payload['description']
        )

        self.assertEqual(
            updated_resource['avatarId'],
            resource['avatarId']
        )

        self.assertIn(
            'avatarURL',
            updated_resource
        )

        self.is_cloudfront_url(updated_resource['avatarURL'])
        self.num_resources(1)

    def test_student_cannot_update_others_resource_description(self):
        self.num_resources(0)
        self.req = create_test_request(self.student2)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'description': 'description v2'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 403)

        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertNotEqual(
            data['description']['text'],
            payload['description']
        )

        self.num_resources(1)

    def test_student_can_update_own_avatar_image(self):
        self.num_resources(0)
        self.req = create_test_request(self.student)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'avatar': self.test_file2
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_resource = self.json(req)
        self.assertEqual(
            updated_resource['displayName']['text'],
            resource['displayName']['text']
        )

        self.assertEqual(
            updated_resource['description']['text'],
            resource['description']['text']
        )

        self.assertNotEqual(
            updated_resource['avatarId'],
            resource['avatarId']
        )

        self.assertIn(
            'avatarURL',
            updated_resource
        )

        self.is_cloudfront_url(updated_resource['avatarURL'])
        self.num_resources(1)

        expected_name = self.filename(self.test_file2).split('.')[0]
        self.assertIn(
            expected_name,
            updated_resource['avatarURL']
        )

    def test_when_updating_avatar_previous_file_is_deleted(self):
        self.num_resources(0)
        self.req = create_test_request(self.student)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        original_s3_path = self.get_resource_avatar_url_key(resource['id'])
        self.assertTrue(self.s3_file_exists(original_s3_path))

        payload = {
            'avatar': self.test_file2
        }

        req = self.client.put(url, payload)
        self.updated(req)

        self.assertFalse(self.s3_file_exists(original_s3_path))

    def test_student_cannot_update_anothers_avatar(self):
        self.num_resources(0)
        self.req = create_test_request(self.student2)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'avatar': self.test_file2
        }

        req = self.client.put(url, payload)
        self.code(req, 403)

        req = self.client.get(url)
        self.ok(req)

        data = self.json(req)
        self.assertEqual(
            data['displayName']['text'],
            resource['displayName']['text']
        )

        self.assertEqual(
            data['description']['text'],
            resource['description']['text']
        )

        self.assertEqual(
            data['avatarId'],
            resource['avatarId']
        )

        self.assertIn(
            'avatarURL',
            data
        )

        self.is_cloudfront_url(data['avatarURL'])
        self.num_resources(1)

        unexpected_name = self.filename(self.test_file2).split('.')[0]
        self.assertNotIn(
            unexpected_name,
            data['avatarURL']
        )

    def test_update_with_no_parameters_throws_exception(self):
        self.num_resources(0)
        self.req = create_test_request(self.student)
        resource = self.setup_resource(self.bin['id'])
        self.num_resources(1)

        self.login(non_instructor=True)
        url = self.url + 'bins/' + self.bin['id'] + '/resources/' + resource['id']

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"name\\", \\"description\\", \\"files\\"')
        self.num_resources(1)

