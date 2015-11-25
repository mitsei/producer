import boto
import envoy

from assessments.tests.test_views import AssessmentTestCase

from boto.s3.key import Key

from copy import deepcopy

from dlkit.mongo.records.types import COMPOSITION_RECORD_TYPES, EDX_COMPOSITION_GENUS_TYPES,\
    REPOSITORY_GENUS_TYPES, REPOSITORY_RECORD_TYPES, ASSET_RECORD_TYPES,\
    ASSET_CONTENT_RECORD_TYPES, ITEM_RECORD_TYPES

from dlkit_django.errors import NotFound
from dlkit_django.primordium import Id, DataInputStream, Type

from django.conf import settings
from django.test.utils import override_settings
from django.utils.http import unquote

from dysonx.dysonx import get_or_create_user_repo

from utilities import general as gutils
from utilities import repository as rutils
from utilities.testing import DjangoTestCase, ABS_PATH


LORE_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['lore-repo'])
COURSE_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['course-repo'])
RUN_REPOSITORY = Type(**REPOSITORY_RECORD_TYPES['run-repo'])
USER_REPOSITORY_GENUS = Type(**REPOSITORY_GENUS_TYPES['user-repo'])

EDX_COMPOSITION = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
EDX_CHAPTER = Type(**EDX_COMPOSITION_GENUS_TYPES['chapter'])
EDX_ASSET = Type(**ASSET_RECORD_TYPES['edx-asset'])
EDX_ASSET_CONTENT = Type(**ASSET_CONTENT_RECORD_TYPES['edx-asset-content-text-files'])
EDX_ITEM = Type(**ITEM_RECORD_TYPES['edx_item'])

class RepositoryTestCase(DjangoTestCase):
    """

    """
    def attach_ids_to_composition(self, composition_id, id_list):
        for id_ in id_list:
            self.repo.add_asset(Id(id_), Id(composition_id))

    def create_new_repo(self):
        rm = gutils.get_session_data(self.req, 'rm')
        form = rm.get_repository_form_for_create([])
        form.display_name = 'new repository'
        form.description = 'for testing'
        form.set_genus_type(Type(**REPOSITORY_GENUS_TYPES['domain-repo']))
        return rm.create_repository(form)

    def create_new_course_repo(self):
        rm = gutils.get_session_data(self.req, 'rm')
        form = rm.get_repository_form_for_create([LORE_REPOSITORY, COURSE_REPOSITORY])
        form.display_name = 'new course repository'
        form.description = 'for testing'
        form.set_genus_type(Type(**REPOSITORY_GENUS_TYPES['course-repo']))
        return rm.create_repository(form)

    def create_new_run_repo(self):
        rm = gutils.get_session_data(self.req, 'rm')
        form = rm.get_repository_form_for_create([LORE_REPOSITORY, RUN_REPOSITORY])
        form.display_name = 'new run repository'
        form.description = 'for testing'
        form.set_genus_type(Type(**REPOSITORY_GENUS_TYPES['course-run-repo']))
        return rm.create_repository(form)

    def create_new_user_repo(self):
        rm = gutils.get_session_data(self.req, 'rm')
        form = rm.get_repository_form_for_create([LORE_REPOSITORY])
        form.display_name = 'new user repository'
        form.description = 'for testing'
        form.set_genus_type(USER_REPOSITORY_GENUS)
        return rm.create_repository(form)

    def get_asset(self, asset_id):
        return self.repo.get_asset(Id(asset_id))

    def get_repo(self, repo_id):
        if not isinstance(repo_id, Id):
            repo_id = Id(repo_id)
        rm = gutils.get_session_data(self.req, 'rm')
        return rm.get_repository(repo_id)

    def num_assets(self, val, repo=None):
        if repo is None:
            repo = self.repo
        self.assertEqual(
            self.get_repo(repo.ident).get_assets().available(),
            val
        )

    def num_compositions(self, val, repo=None, unsequestered=False):
        if repo is None:
            repo = self.get_repo(self.repo.ident)
        if unsequestered:
            repo.use_unsequestered_composition_view()
        else:
            repo.use_sequestered_composition_view()
        self.assertEqual(
            repo.get_compositions().available(),
            val
        )

    def num_repos(self, val):
        rm = gutils.get_session_data(self.req, 'rm')

        self.assertEqual(
            rm.repositories.available(),
            val
        )

    def s3_file_exists(self, key):
        connection = boto.connect_s3(settings.S3_TEST_PUBLIC_KEY,
                                     settings.S3_TEST_PRIVATE_KEY)
        bucket = connection.create_bucket(settings.S3_BUCKET)
        file_ = Key(bucket, key)
        return file_.exists()

    def setUp(self):
        super(RepositoryTestCase, self).setUp()
        self.url = self.base_url + 'repository/'

    def setup_asset(self, repository_id, with_lo=False):
        if not isinstance(repository_id, Id):
            repository_id = Id(repository_id)

        test_file = '/repository/tests/files/Flexure_structure_with_hints.pdf'

        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(repository_id)
        asset_form = repo.get_asset_form_for_create([EDX_ASSET])
        asset_form.display_name = 'test'
        asset_form.description = 'ing'

        if with_lo:
            self._lo = 'mc3-objective%3A9729%40MIT-OEIT'
            asset_form.set_learning_objective_ids([Id(self._lo)])

        new_asset = repo.create_asset(asset_form)

        # now add the new data
        asset_content_type_list = [EDX_ASSET_CONTENT]
        try:
            config = repo._runtime.get_configuration()
            parameter_id = Id('parameter:assetContentRecordTypeForFiles@mongo')
            asset_content_type_list.append(
                config.get_value_by_parameter(parameter_id).get_type_value())
        except AttributeError:
            pass

        asset_content_form = repo.get_asset_content_form_for_create(new_asset.ident,
                                                                    asset_content_type_list)

        self.default_asset_file = ABS_PATH + test_file
        with open(self.default_asset_file, 'r') as file_:
            asset_content_form.set_data(DataInputStream(file_))

        asset_content_form.set_text('<foo>bar</foo>')

        repo.create_asset_content(asset_content_form)

        new_asset = repo.get_asset(new_asset.ident)
        return new_asset

    def setup_composition(self, repository_id, with_lo=False):
        if isinstance(repository_id, basestring):
            repository_id = Id(repository_id)
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(repository_id)

        # new_asset = self.setup_asset(repository_id)

        form = repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'my test composition'
        form.description = 'foobar'
        form.set_children([])
        # form.set_children([new_asset.ident])

        if with_lo:
            form.set_genus_type(EDX_CHAPTER)
            self._lo = 'mc3-objective%3A9729%40MIT-OEIT'
            form.set_learning_objective_ids([Id(self._lo)])

        composition = repo.create_composition(form)
        return composition

    def tearDown(self):
        super(RepositoryTestCase, self).tearDown()


class AssetCrUDTests(RepositoryTestCase):
    """Test the views for repository crud

    """
    def setUp(self):
        super(AssetCrUDTests, self).setUp()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40EDX.ORG'
        self.repo = self.create_new_repo()
        self.repo_id = unquote(str(self.repo.ident))

        test_file = '/repository/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/repository/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.login()

        self.url += 'assets/'

    def tearDown(self):
        super(AssetCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_repository_assets(self):
        self.setup_asset(self.repo_id)
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        assets = self.json(req)['data']['results']
        self.assertEqual(
            len(assets),
            1
        )
        asset_contents = assets[0]['assetContents']
        # deprecated_asset_contents = assets[0]['assetContent']

        self.assertEqual(
            len(asset_contents),
            1
        )
        #
        # self.assertEqual(
        #     asset_contents,
        #     deprecated_asset_contents
        # )

        self.is_cloudfront_url(asset_contents[0]['url'])

    def test_student_can_view_assets(self):
        self.setup_asset(self.repo_id)
        self.login(non_instructor=True)
        url = self.url
        req = self.client.get(url)
        self.ok(req)

    def test_can_create_single_asset(self):
        url = self.url
        payload = {
            'my_asset_label': self.test_file,
            'repositoryId': str(self.repo.ident)
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
        url = self.url
        payload = {
            'my_asset_label': self.test_file,
            'my_second_asset': self.test_file2,
            'repositoryId': str(self.repo.ident)
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
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))
        req = self.client.get(url)
        self.ok(req)
        asset_map = self.json(req)
        self.assertEqual(
            str(asset.ident),
            asset_map['id']
        )
        self.assertEqual(
            asset.display_name.text,
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
            return url.split('.net')[-1].split('?')[0]

        asset = self.setup_asset(self.repo_id)
        s3_url = asset.get_asset_contents().next().url
        s3_path = get_s3_path(s3_url)
        self.assertTrue(self.s3_file_exists(s3_path))

        url = self.url + unquote(str(asset.ident))
        req = self.client.delete(url)
        self.deleted(req)

        self.assertFalse(self.s3_file_exists(s3_path))

    def test_can_update_asset_name(self):
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'displayName': 'name v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_asset = self.json(req)
        self.assertEqual(
            updated_asset['displayName']['text'],
            payload['displayName']
        )

        self.assertEqual(
            asset.description.text,
            updated_asset['description']['text']
        )

        self.assertEqual(
            asset.object_map['assetContents'],
            updated_asset['assetContents']
        )

    def test_can_update_asset_objectives(self):
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'learningObjectiveIds': ['mc3-objective%3A9730%40MIT-OEIT']
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_asset = self.json(req)
        self.assertEqual(
            updated_asset['learningObjectiveIds'],
            payload['learningObjectiveIds']
        )

    def test_can_update_asset_description(self):
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'description': 'desc v2'
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset.display_name.text
        self.assertEqual(
            updated_asset['displayName']['text'],
            asset_name
        )
        updated_asset_obj = self.get_asset(updated_asset['id'])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset.display_name.text
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            payload['description']
        )

        self.assertEqual(
            updated_asset_obj.object_map['assetContents'],
            asset.object_map['assetContents']
        )

    def test_can_update_asset_file_with_single_file(self):
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'file2': self.test_file
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset.display_name.text
        self.assertEqual(
            updated_asset['displayName']['text'],
            asset_name
        )
        updated_asset_obj = self.get_asset(updated_asset['id'])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset.display_name.text
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset.description.text
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
        asset = self.setup_asset(self.repo_id)
        original_s3_url = asset.get_asset_contents().next().url
        url = self.url + unquote(str(asset.ident))

        payload = {
            'file2': self.test_file
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset.display_name.text
        self.assertEqual(
            updated_asset['displayName']['text'],
            asset_name
        )

        updated_asset_obj = self.get_asset(updated_asset['id'])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset.display_name.text
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset.description.text
        )

        updated_ac_map = updated_asset_obj.object_map['assetContents']

        self.assertNotEqual(
            updated_ac_map,
            asset.object_map['assetContents']
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
        self.assertFalse(self.s3_file_exists(original_s3_url.split('.net')[1].split('?')[0]))

    def test_can_update_asset_file_with_multiple_files(self):
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'file2': self.test_file,
            'file3': self.test_file2
        }

        req = self.client.put(url, payload)
        self.updated(req)

        updated_asset = self.json(req)
        asset_name = asset.display_name.text
        self.assertEqual(
            updated_asset['displayName']['text'],
            asset_name
        )
        updated_asset_obj = self.get_asset(updated_asset['id'])
        self.assertEqual(
            updated_asset_obj.display_name.text,
            asset.display_name.text
        )

        self.assertEqual(
            updated_asset_obj.description.text,
            asset.description.text
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
        asset = self.setup_asset(self.repo_id)
        url = self.url + unquote(str(asset.ident))

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"displayName\\", \\"description\\", \\"files\\"')

    def test_can_get_asset_learning_objectives(self):
        asset = self.setup_asset(self.repo_id, with_lo=True)
        url = '{0}{1}/objectives/'.format(self.url,
                                          unquote(str(asset.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            self._lo
        )

    def test_getting_asset_los_when_has_none_returns_empty_list(self):
        asset = self.setup_asset(self.repo_id, with_lo=False)
        url = '{0}{1}/objectives/'.format(self.url,
                                          unquote(str(asset.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            0
        )


class BasicServiceTests(RepositoryTestCase):
    """Test the views for getting the basic service calls

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()
        self.url += 'repositories/'

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_instructors_can_get_list_of_repositories(self):
        self.login()
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        self.message(req, '"count": 0')

    def test_learners_can_see_list_of_repositories(self):
        self.login(non_instructor=True)
        url = self.url
        req = self.client.get(url)
        self.ok(req)


class CompositionCrUDTests(AssessmentTestCase, RepositoryTestCase):
    """Test the views for composition crud

    """
    def setUp(self):
        super(CompositionCrUDTests, self).setUp()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40EDX.ORG'
        self.repo = self.create_new_repo()
        self.repo_id = unquote(str(self.repo.ident))

        test_file = '/repository/tests/files/ps_2015_beam_2gages.pdf'
        test_file2 = '/repository/tests/files/Backstage_v2_quick_guide.docx'

        self.test_file = open(ABS_PATH + test_file, 'r')
        self.test_file2 = open(ABS_PATH + test_file2, 'r')

        self.login()

        # reset this, because AssessmentTestCase will make it assessment/
        self.url = self.base_url + 'repository/compositions/'

    def tearDown(self):
        super(CompositionCrUDTests, self).tearDown()
        self.test_file.close()
        self.test_file2.close()

    def test_can_get_repository_compositions(self):
        self.setup_composition(self.repo_id)
        url = self.url
        req = self.client.get(url)
        self.ok(req)
        compositions = self.json(req)['data']['results']
        self.assertEqual(
            len(compositions),
            1
        )

    def test_can_create_composition_without_children(self):
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'repositoryId': str(self.repo.ident)
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
            payload['displayName']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_create_composition_with_single_nonlist_child_id(self):
        new_asset = self.setup_asset(self.repo_id)
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'childIds': str(new_asset.ident),
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            str(new_asset.ident),
            composition['childIds'][0]
        )
        self.assertEqual(
            len(composition['childIds']),
            1
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_can_create_composition_with_asset_child_id_in_list(self):
        new_asset = self.setup_asset(self.repo_id)
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'childIds': [str(new_asset.ident)],
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            str(new_asset.ident),
            composition['childIds'][0]
        )
        self.assertEqual(
            len(composition['childIds']),
            1
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            composition['description']['text'],
            payload['description']
        )

    def test_missing_parameters_in_create_throw_exceptions(self):
        self.num_compositions(0)
        url = self.url

        payload = {
            'displayName': 'test composition',
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
        self.setup_composition(self.repo_id)
        self.num_compositions(1)

        url = self.url + '123foo'
        req = self.client.delete(url)
        self.code(req, 500)
        self.num_compositions(1)

    def test_user_can_delete_own_composition(self):
        user_repo = get_or_create_user_repo(self.user.username)
        self.num_compositions(0, repo=user_repo)
        composition = self.setup_composition(user_repo.ident)
        self.num_compositions(1, repo=user_repo)

        url = self.url + unquote(str(composition.ident))
        req = self.client.delete(url)
        self.deleted(req)
        self.num_compositions(0, repo=user_repo)

    def test_can_get_composition_details(self):
        new_composition = self.setup_composition(self.repo_id)
        url = self.url + unquote(str(new_composition.ident))

        req = self.client.get(url)
        self.ok(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            new_composition.display_name.text
        )
        self.assertEqual(
            composition['description']['text'],
            new_composition.description.text
        )
        self.assertIn(
            '_links',
            composition
        )

    def test_can_update_composition_attributes(self):
        composition = self.setup_composition(self.repo_id, with_lo=True)
        url = self.url + unquote(str(composition.ident))

        test_cases = [{'displayName': 'ha'},
                      {'description': 'funny'},
                      {'learningObjectiveIds': ['mc3-objective%3A9730%40MIT-OEIT']}]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)
            key = payload.keys()[0]
            if key in ['displayName', 'description']:
                self.assertEqual(
                    data[key]['text'],
                    payload[key]
                )
            else:
                self.assertEqual(
                    data[key],
                    payload[key]
                )

    def test_update_with_no_parameters_throws_exception(self):
        new_composition = self.setup_composition(self.repo_id)
        url = self.url + unquote(str(new_composition.ident))

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url,
                              data=payload,
                              format='json')
        self.code(req, 500)
        self.message(req,
                     'At least one of the following must be passed in: [\\"displayName\\", \\"description\\", \\"childIds\\"')

    def test_can_get_composition_assets(self):
        asset = self.setup_asset(self.repo_id)
        composition = self.setup_composition(self.repo_id)
        self.attach_ids_to_composition(str(composition.ident), [str(asset.ident)])

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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
            str(asset.ident)
        )
        self.assertEqual(
            assets[0]['displayName']['text'],
            asset.display_name.text
        )

        self.assertEqual(
            assets[0]['description']['text'],
            asset.description.text
        )

    def test_asset_urls_point_to_root_asset_details(self):
        asset = self.setup_asset(self.repo_id)
        composition = self.setup_composition(self.repo_id)
        self.attach_ids_to_composition(str(composition.ident), [str(asset.ident)])

        url = self.url + unquote(str(composition.ident)) + '/assets/'
        self.login()
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        asset_url = data['data']['results'][0]['_link']
        self.assertIn(
            unquote('/repository/compositions/' + str(composition.ident) +
                    '/assets/../../../assets/' + str(asset.ident) + '/'),
            asset_url
        )

    def test_can_get_compositions_enclosed_assets(self):
        self.num_assets(0)

        bank = self.create_assessment_bank()
        item = self.create_item(bank)
        assessment = self.create_assessment_for_item(bank, item)

        composition = self.setup_composition(self.repo_id)
        self.num_assets(0)

        self.attach_ids_to_composition(str(composition.ident), [str(assessment.ident)])

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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

        self.num_assets(1)

    def test_can_attach_one_asset_to_composition(self):
        composition = self.setup_composition(self.repo_id)
        asset = self.setup_asset(self.repo_id)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': str(asset.ident)
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
            str(asset.ident)
        )

    def test_can_attach_one_non_asset_to_composition(self):
        composition = self.setup_composition(self.repo_id)

        bank = self.create_assessment_bank()
        item = self.create_item(bank)
        assessment = self.create_assessment_for_item(bank, item)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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
        composition = self.setup_composition(self.repo_id)
        asset = self.setup_asset(self.repo_id)
        asset2 = self.setup_asset(self.repo_id)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
        self.login()

        req = self.client.get(url)
        data = self.json(req)

        self.assertEqual(
            len(data['data']['results']),
            0
        )

        payload = {
            'assetIds': [str(asset.ident), str(asset2.ident)]
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
            str(asset.ident)
        )
        self.assertEqual(
            assets[1]['id'],
            str(asset2.ident)
        )

    def test_can_attach_multiple_non_assets_to_composition(self):
        composition = self.setup_composition(self.repo_id)
        bank = self.create_assessment_bank()
        item = self.create_item(bank)
        assessment = self.create_assessment_for_item(bank, item)

        bank2 = self.create_assessment_bank()
        item2 = self.create_item(bank2)
        assessment2 = self.create_assessment_for_item(bank2, item2)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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

        asset = self.setup_asset(self.repo_id)
        composition = self.setup_composition(self.repo_id)
        self.num_assets(1)

        self.attach_ids_to_composition(str(composition.ident), [str(asset.ident)])

        url = self.url + unquote(str(composition.ident)) + '/assets/'
        self.login()

        payload = {
            'foo': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     '\\"assetIds\\" required in input parameters but not provided.')

    def test_cannot_edit_some_enclosed_asset_attributes(self):
        composition = self.setup_composition(self.repo_id)
        bank = self.create_assessment_bank()
        item = self.create_item(bank)
        assessment = self.create_assessment_for_item(bank, item)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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

        url = self.base_url + 'repository/assets/' + enclosure_id + '/'

        payload = {
            'displayName': 'foo',
            'description': 'bar'
        }

        req = self.client.put(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'You cannot edit those fields.')

    def test_can_add_files_to_enclosed_assets(self):
        composition = self.setup_composition(self.repo_id)
        bank = self.create_assessment_bank()
        item = self.create_item(bank)
        assessment = self.create_assessment_for_item(bank, item)

        url = self.url + unquote(str(composition.ident)) + '/assets/'
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

        url = self.base_url + 'repository/assets/' + enclosure_id + '/'

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

    def test_adding_asset_id_to_children_creates_sequestered_wrapper(self):
        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1, unsequestered=True)
        url = self.url + unquote(str(composition.ident))

        asset = self.setup_asset(self.repo_id)

        payload = {
            'childIds': str(asset.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            data['childIds'],
            [str(asset.ident)]
        )
        self.assertEqual(
            len(data['childIds']),
            1
        )
        self.num_compositions(2, unsequestered=True)
        self.num_compositions(1)

        wrapper_id = data['childIds'][0]

        self.repo.use_sequestered_composition_view()
        self.assertRaises(NotFound, self.repo.get_composition, Id(wrapper_id))

        self.repo.use_unsequestered_composition_view()
        wrapper = self.repo.get_composition(Id(wrapper_id))
        wrapped_assets = self.repo.get_composition_assets(wrapper.ident)
        self.assertEqual(
            wrapped_assets.available(),
            1
        )
        self.assertEqual(
            str(asset.ident),
            str(wrapped_assets.next().ident)
        )

    def test_removing_asset_children_removes_sequestered_wrappers(self):
        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1, unsequestered=True)
        url = self.url + unquote(str(composition.ident))

        asset = self.setup_asset(self.repo_id)

        payload = {
            'childIds': str(asset.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            data['childIds'],
            [str(asset.ident)]
        )
        self.assertEqual(
            len(data['childIds']),
            1
        )
        self.num_compositions(2, unsequestered=True)
        self.num_compositions(1)

        payload = {
            'childIds': []
        }
        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertEqual(
            data['childIds'],
            []
        )
        self.num_compositions(1, unsequestered=True)
        self.num_compositions(1)

    def test_can_reorder_asset_children_and_wrappers_are_garbage_collected(self):
        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1, unsequestered=True)
        url = self.url + unquote(str(composition.ident))

        asset_1 = self.setup_asset(self.repo_id)
        asset_2 = self.setup_asset(self.repo_id)


        test_cases = [(asset_1, asset_2),
                      (asset_2, asset_1)]

        for case in test_cases:
            a1 = case[0]
            a2 = case[1]
            payload = {
                'childIds': [str(a1.ident), str(a2.ident)]
            }

            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)
            self.assertNotEqual(
                data['childIds'],
                [str(a1.ident), str(a2.ident)]
            )
            self.assertEqual(
                len(data['childIds']),
                2
            )
            self.num_compositions(3, unsequestered=True)
            self.num_compositions(1)

            wrapper_1_id = data['childIds'][0]
            wrapper_2_id = data['childIds'][1]

            self.repo.use_sequestered_composition_view()
            self.assertRaises(NotFound, self.repo.get_composition, Id(wrapper_1_id))
            self.assertRaises(NotFound, self.repo.get_composition, Id(wrapper_2_id))

            self.repo.use_unsequestered_composition_view()
            wrapper_1 = self.repo.get_composition(Id(wrapper_1_id))
            wrapper_2 = self.repo.get_composition(Id(wrapper_2_id))
            wrapped_asset_1 = self.repo.get_composition_assets(wrapper_1.ident)
            wrapped_asset_2 = self.repo.get_composition_assets(wrapper_2.ident)
            self.assertEqual(
                wrapped_asset_1.available(),
                1
            )
            self.assertEqual(
                str(a1.ident),
                str(wrapped_asset_1.next().ident)
            )

            self.assertEqual(
                wrapped_asset_2.available(),
                1
            )
            self.assertEqual(
                str(a2.ident),
                str(wrapped_asset_2.next().ident)
            )

        self.num_compositions(3, unsequestered=True)
        self.num_compositions(1)

    def test_assigning_items_to_composition_also_assign_to_orchestrated_run_bank(self):
        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)

        self.num_compositions(1, unsequestered=True)

        orchestrated_bank = self.get_bank(self.repo_id)

        self.num_items(orchestrated_bank, 0)

        user_repo = get_or_create_user_repo(self.username)
        new_bank = self.get_bank(user_repo.ident)
        item = self.create_item(new_bank)

        self.num_items(new_bank, 1)

        url = self.url + unquote(str(composition.ident))

        payload = {
            'childIds': str(item.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            data['childIds'],
            [str(item.ident)]
        )
        self.assertEqual(
            len(data['childIds']),
            1
        )
        self.num_compositions(2, unsequestered=True)
        self.num_compositions(1)

        self.num_items(orchestrated_bank, 1)
        self.num_items(new_bank, 1)

    def test_assigning_assets_to_composition_does_not_assign_to_run_repo(self):
        from dysonx.dysonx import get_or_create_user_repo

        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)

        self.num_compositions(1, unsequestered=True)

        user_repo = get_or_create_user_repo(self.username)
        asset = self.setup_asset(user_repo.ident)

        self.num_assets(1, user_repo)
        self.num_assets(0)

        url = self.url + unquote(str(composition.ident))

        payload = {
            'childIds': str(asset.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            data['childIds'],
            [str(asset.ident)]
        )
        self.assertEqual(
            len(data['childIds']),
            1
        )
        self.num_compositions(2, unsequestered=True)
        self.num_compositions(1)

        self.num_assets(1, user_repo)
        self.num_assets(0)

    def test_user_cannot_delete_composition_when_not_theirs(self):
        self.num_compositions(0, unsequestered=True)
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1, unsequestered=True)
        url = self.url + unquote(str(composition.ident))

        asset = self.setup_asset(self.repo_id)

        payload = {
            'childIds': str(asset.ident)
        }
        req = self.client.put(url, payload, format='json')
        self.updated(req)
        self.num_compositions(2, unsequestered=True)
        url += '?withChildren'
        req = self.client.delete(url)
        self.code(req, 500)
        self.num_compositions(2, unsequestered=True)

    def test_can_delete_children_of_composition_with_flag(self):
        user_repo = get_or_create_user_repo(self.username)

        self.num_compositions(0, repo=user_repo, unsequestered=True)
        composition = self.setup_composition(user_repo.ident)
        self.num_compositions(1, repo=user_repo, unsequestered=True)
        url = self.url + unquote(str(composition.ident))

        asset = self.setup_asset(user_repo.ident)

        payload = {
            'childIds': str(asset.ident)
        }
        req = self.client.put(url, payload, format='json')
        self.updated(req)
        self.num_compositions(2, repo=user_repo, unsequestered=True)
        url += '?withChildren'
        req = self.client.delete(url)
        self.deleted(req)
        self.num_compositions(0, repo=user_repo, unsequestered=True)

    def test_adding_composition_to_new_repo_does_not_assign_it(self):
        repo1 = self.repo
        repo2 = self.create_new_repo()
        composition = self.setup_composition(repo2.ident)

        self.num_compositions(0)
        self.num_compositions(1, repo=repo2)

        payload = {
            'childIds': [str(composition.ident)]
        }

        url = self.base_url + 'repository/repositories/' + unquote(str(repo1.ident))

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        self.num_compositions(0, repo=repo1)
        self.num_compositions(1, repo=repo2)

    def test_adding_composition_does_not_automatically_assign_it(self):
        repo1 = self.repo
        repo2 = self.create_new_repo()
        composition = self.setup_composition(repo2.ident)

        self.num_compositions(0)
        self.num_compositions(1, repo=repo2)

        payload = {
            'childIds': [str(composition.ident)]
        }

        url = self.base_url + 'repository/repositories/' + unquote(str(repo1.ident))

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        self.num_compositions(0)
        self.num_compositions(1, repo=repo2)

    def test_deleting_composition_with_multiple_catalogs_requires_parent_id(self):
        repo1 = self.repo
        repo2 = self.create_new_repo()
        composition = self.setup_composition(repo2.ident)

        self.num_compositions(0)
        self.num_compositions(1, repo=repo2)

        payload = {
            'childIds': [str(composition.ident)]
        }

        url = self.base_url + 'repository/repositories/' + unquote(str(repo1.ident))

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        # manually assign composition to repo1
        rm = gutils.get_session_data(self.req, 'rm')
        rm.assign_composition_to_repository(composition.ident, repo1.ident)

        url = self.url + str(composition.ident)
        req = self.client.delete(url)
        self.code(req, 500)
        self.num_compositions(1)
        self.num_compositions(1, repo=repo2)

    # DEPRECATED -- THIS DOES NOT HAPPEN ANYMORE BECAUSE WE DON'T ASSIGN TO MULTIPLE
    # FOR AUTHZ REASONS
    # def test_removing_composition_from_one_repo_does_not_delete_it_from_db(self):
    #     repo1 = self.repo
    #     repo2 = self.create_new_repo()
    #     composition = self.setup_composition(repo2.ident)
    #
    #     self.num_compositions(0)
    #     self.num_compositions(1, repo=repo2)
    #
    #     payload = {
    #         'childIds': [str(composition.ident)]
    #     }
    #
    #     url = self.base_url + 'repository/repositories/' + unquote(str(repo1.ident))
    #
    #     req = self.client.put(url, payload, format='json')
    #     self.updated(req)
    #
    #     # manually assign composition to repo1
    #     rm = gutils.get_session_data(self.req, 'rm')
    #     rm.assign_composition_to_repository(composition.ident, repo1.ident)
    #
    #     self.num_compositions(1)
    #     self.num_compositions(1, repo=repo2)
    #
    #     url = self.url + str(composition.ident)
    #
    #     payload = {
    #         'repoId': str(repo1.ident)
    #     }
    #     req = self.client.delete(url, payload, format='json')
    #     self.deleted(req)
    #     self.num_compositions(0)
    #     self.num_compositions(1, repo=repo2)

    def test_removing_composition_also_removes_references_in_other_repos(self):
        repo1 = self.repo
        repo2 = self.create_new_repo()
        user_repo = get_or_create_user_repo(self.user.username)

        rm = gutils.get_session_data(self.req, 'rm')
        rm.add_child_repository(user_repo.ident, repo1.ident)
        rm.add_child_repository(user_repo.ident, repo2.ident)

        composition1 = self.setup_composition(repo1.ident)
        composition2 = self.setup_composition(repo2.ident)

        self.num_compositions(1)
        self.num_compositions(1, repo=repo2)

        payload = {
            'childIds': [str(composition1.ident)]
        }

        url = self.base_url + 'repository/compositions/' + unquote(str(composition2.ident))

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        composition2 = repo2.get_composition(composition2.ident)
        self.assertIn(
            str(composition1.ident),
            [str(i) for i in composition2.get_child_ids()]
        )

        url = self.base_url + 'repository/compositions/' + unquote(str(composition1.ident))
        req = self.client.delete(url)
        self.deleted(req)

        composition2 = repo2.get_composition(composition2.ident)
        self.assertEqual(
            [],
            [str(i) for i in composition2.get_child_ids()]
        )

    def test_if_composition_child_not_found_filler_warning_returned(self):
        repo1 = self.repo
        repo2 = self.create_new_repo()

        user_repo = get_or_create_user_repo(self.user.username)

        rm = gutils.get_session_data(self.req, 'rm')
        rm.add_child_repository(user_repo.ident, repo1.ident)

        composition1 = self.setup_composition(repo1.ident)
        composition2 = self.setup_composition(repo2.ident)

        self.num_compositions(1)
        self.num_compositions(1, repo=repo2)

        payload = {
            'childIds': [str(composition1.ident)]
        }

        url = self.base_url + 'repository/compositions/' + unquote(str(composition2.ident))

        req = self.client.put(url, payload, format='json')
        self.updated(req)

        composition2 = repo2.get_composition(composition2.ident)
        self.assertIn(
            str(composition1.ident),
            [str(i) for i in composition2.get_child_ids()]
        )

        # Now delete composition1 manually...as if the dangling reference cleaner
        # did not work
        repo1.delete_composition(composition1.ident)

        composition2 = repo2.get_composition(composition2.ident)
        self.assertIn(
            str(composition1.ident),
            [str(i) for i in composition2.get_child_ids()]
        )

        # Now getting children of composition2 should show a filler composition
        # with a warning

        url = self.base_url + 'repository/repositories/' + unquote(str(repo2.ident)) + '/compositions/' + unquote(str(composition2.ident)) + '/children/'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            1,
            data['data']['count']
        )

        self.assertEqual(
            str(Type(**EDX_COMPOSITION_GENUS_TYPES['error-deleted'])),
            data['data']['results'][0]['genusTypeId']
        )

    def test_can_get_composition_learning_objectives(self):
        composition = self.setup_composition(self.repo_id, with_lo=True)
        url = '{0}{1}/objectives/'.format(self.url,
                                          unquote(str(composition.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            self._lo
        )

    def test_getting_composition_los_when_has_none_returns_empty_list(self):
        composition = self.setup_composition(self.repo_id, with_lo=False)
        url = '{0}{1}/objectives/'.format(self.url,
                                          unquote(str(composition.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            0
        )


class CompositionEndpointTests(RepositoryTestCase):
    """Test the views for composition "extensions", like /children and /offerings

    """
    def setUp(self):
        super(CompositionEndpointTests, self).setUp()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40EDX.ORG'
        self.repo = self.create_new_repo()
        self.repo_id = unquote(str(self.repo.ident))

        self.login()

        self.course = self.setup_composition_with_genus(self.repo, 'course')
        self.offering = self.setup_composition_with_genus(self.repo, 'offering')
        self.chapter = self.setup_composition_with_genus(self.repo, 'chapter')
        self.resource_node = self.setup_composition_with_genus(self.repo, 'resource-node')

        self.asset = self.setup_asset(self.repo.ident)
        self.repo.add_asset(self.asset.ident, self.resource_node.ident)
        rutils.append_child_composition(self.repo, self.course, self.offering)
        rutils.append_child_composition(self.repo, self.offering, self.chapter)
        rutils.append_child_composition(self.repo, self.offering, self.resource_node)

        # reset this, because AssessmentTestCase will make it assessment/
        self.url = self.base_url + 'repository/compositions/'

    def setup_composition_with_genus(self, repository, genus):
        genus_type = Type(**EDX_COMPOSITION_GENUS_TYPES[genus])

        form = repository.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'my test composition'
        form.description = 'foobar'
        form.set_children([])
        form.set_genus_type(genus_type)

        if genus == 'resource-node':
            form.set_sequestered(True)

        composition = repository.create_composition(form)

        return composition

    def tearDown(self):
        super(CompositionEndpointTests, self).tearDown()

    def test_can_get_course_offerings(self):
        url = self.url + str(self.course.ident) + '/offerings'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(self.offering.ident)
        )

    def test_trying_to_get_offerings_of_non_course_throws_exception(self):
        url = self.url + str(self.offering.ident) + '/offerings'
        req = self.client.get(url)
        self.code(req, 500)

    def test_can_get_children_of_offering(self):
        url = self.url + str(self.offering.ident) + '/children'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            2
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(self.chapter.ident)
        )
        self.assertEqual(
            data['data']['results'][1]['id'],
            str(self.asset.ident)
        )

    def test_can_clone_composition(self):
        user_repo = get_or_create_user_repo(self.username)
        self.num_compositions(0, repo=user_repo, unsequestered=True)
        self.num_compositions(4, repo=self.repo, unsequestered=True)

        url = self.url + str(self.chapter.ident) + '/unlock/'
        req = self.client.post(url)
        self.created(req)
        data = self.json(req)

        self.assertNotEqual(
            data['id'],
            str(self.chapter.ident)
        )

        self.assertEqual(
            data['displayName']['text'],
            self.chapter.display_name.text
        )

        self.assertEqual(
            data['description']['text'],
            self.chapter.description.text
        )

        self.num_compositions(1, repo=user_repo, unsequestered=True)
        self.num_compositions(4, repo=self.repo, unsequestered=True)


class EdXCompositionCrUDTests(RepositoryTestCase):
    """Test the views for composition crud

    """
    def setUp(self):
        super(EdXCompositionCrUDTests, self).setUp()
        self.login()
        self.repo = self.create_new_repo()
        self.repo_id = unquote(str(self.repo.ident))
        self.url += 'compositions/'

    def tearDown(self):
        super(EdXCompositionCrUDTests, self).tearDown()

    def test_can_create_edx_composition_with_genus_type(self):
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-composition%3Avertical%40EDX.ORG',
            'repositoryId': str(self.repo.ident)
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
            payload['displayName']
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

    def test_throw_exception_if_bad_genus_type_provided(self):
        self.num_compositions(0)
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-filly',
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.code(req, 500)
        self.message(req,
                     'Bad genus type provided.')

        self.num_compositions(0)

    def test_can_set_edx_composition_values_on_create_chapter(self):
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
            'repositoryId': str(self.repo.ident),
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

        req = self.client.post(url, data=payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['displayName']
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
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-composition%3Avertical%40EDX.ORG',
            'draft': True,
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, data=payload, format='json')
        self.created(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            0
        )
        self.assertEqual(
            composition['displayName']['text'],
            payload['displayName']
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
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
            'repositoryId': str(self.repo.ident),
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

        req = self.client.post(url, data=payload, format='json')
        composition = self.json(req)
        url = self.url + composition['id']

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
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'genusTypeId': 'edx-composition%3Avertical%40EDX.ORG',
            'draft': True,
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, data=payload, format='json')
        composition = self.json(req)

        url = self.url + composition['id']

        payload2 = {
            'draft': False
        }

        req = self.client.put(url, payload2, format='json')
        self.updated(req)
        composition2 = self.json(req)

        self.assertFalse(composition2['draft'])

    def test_can_query_compositions_by_type(self):
        self.num_compositions(0)
        self.setup_composition(self.repo_id)
        self.num_compositions(1)

        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing querying',
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
            'repositoryId': str(self.repo.ident),
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
            payload['displayName']
        )
        self.assertEqual(
            comp['description']['text'],
            payload['description']
        )

    def test_bad_query_type_throws_exception(self):
        self.num_compositions(0)
        self.setup_composition(self.repo_id)
        self.num_compositions(1)

        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing querying',
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
            'repositoryId': str(self.repo.ident),
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

    def test_can_query_for_nested_compositions(self):
        run_repo = self.create_new_run_repo()
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'repositoryId': str(run_repo.ident),
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition2 = self.json(req)

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'repositoryId': str(run_repo.ident),
            'genusTypeId': 'edx-composition%3Asequential%40EDX.ORG',
            'parentId': composition2['id']
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)

        url = self.base_url + 'repository/repositories/' + str(run_repo.ident) + '/compositions/?nested'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            composition2['id']
        )
        self.assertEqual(
            len(data['data']['results'][0]['children']),
            1
        )
        self.assertEqual(
            data['data']['results'][0]['children'][0]['id'],
            composition['id']
        )


class EdXAssetUnitTests(RepositoryTestCase):
    """Test the basic query functionality for assets

    """
    def set_up_user_course(self):
        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential = self.repo.create_composition(form)

        form = self.repo.get_asset_form_for_create([EDX_ASSET])
        form.display_name = 'asset'
        asset = self.repo.create_asset(form)
        self.repo.add_asset(asset.ident, sequential.ident)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential2'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential2 = self.repo.create_composition(form)

        form = self.repo.get_asset_form_for_create([EDX_ASSET])
        form.display_name = 'asset2'
        asset2 = self.repo.create_asset(form)
        self.repo.add_asset(asset2.ident, sequential2.ident)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'chapter'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['chapter']))
        form.set_children([sequential.ident])
        chapter = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'run'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['offering']))
        form.set_children([chapter.ident])
        form.set_sequestered(True)
        run = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'test course'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['course']))
        form.set_children([run.ident])
        form.set_sequestered(True)
        return self.repo.create_composition(form)

    def setUp(self):
        super(EdXAssetUnitTests, self).setUp()
        self.login()
        self.repo = self.create_new_user_repo()
        self.repo_id = unquote(str(self.repo.ident))

    def tearDown(self):
        super(EdXAssetUnitTests, self).tearDown()

    def test_can_query_descendant_compositions_for_assets(self):
        # create course composition, then run, then chapter, then sequential
        # query that the sequential is found when querying descendants of run
        course_composition = self.set_up_user_course()

        querier = self.repo.get_asset_query()
        querier.match_composition_descendants(course_composition.ident, self.repo.ident, True)
        matches = self.repo.get_assets_by_query(querier)
        self.assertEqual(
            matches.available(),
            1
        )
        self.assertEqual(
            matches.next().display_name.text,
            'asset'
        )


class EdXCompositionUnitTests(RepositoryTestCase):
    """Test the basic unit functionality for compositions

    """
    def set_up_user_course(self):
        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential2'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential2 = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'chapter'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['chapter']))
        form.set_children([sequential.ident])
        chapter = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'run'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['offering']))
        form.set_children([chapter.ident])
        form.set_sequestered(True)
        run = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'test course'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['course']))
        form.set_children([run.ident])
        form.set_sequestered(True)
        return self.repo.create_composition(form)

    def setUp(self):
        super(EdXCompositionUnitTests, self).setUp()
        self.login()
        self.repo = self.create_new_user_repo()
        self.repo_id = unquote(str(self.repo.ident))

    def tearDown(self):
        super(EdXCompositionUnitTests, self).tearDown()

    def test_can_query_descendant_compositions(self):
        # create course composition, then run, then chapter, then sequential
        # query that the sequential is found when querying descendants of run
        course_composition = self.set_up_user_course()

        self.repo.use_unsequestered_composition_view()
        querier = self.repo.get_composition_query()
        querier.match_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']), True)
        querier.match_composition_descendants(course_composition.ident, self.repo.ident, True)
        matches = self.repo.get_compositions_by_query(querier)
        self.assertEqual(
            matches.available(),
            1
        )
        self.assertEqual(
            matches.next().display_name.text,
            'sequential'
        )


class EdXItemUnitTests(AssessmentTestCase, RepositoryTestCase):
    """Test the basic query functionality for edX items relative to compositions

    """
    def set_up_user_course(self):
        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential = self.repo.create_composition(form)

        form = self.bank.get_item_form_for_create([EDX_ITEM])
        form.display_name = 'item'
        item = self.bank.create_item(form)

        form = self.bank.get_assessment_form_for_create([])
        form.display_name = 'assessment'
        assessment = self.bank.create_assessment(form)
        self.bank.add_item(assessment.ident, item.ident)

        self.repo.add_asset(assessment.ident, sequential.ident)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'sequential2'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['sequential']))
        sequential2 = self.repo.create_composition(form)

        form = self.bank.get_item_form_for_create([EDX_ITEM])
        form.display_name = 'item2'
        item2 = self.bank.create_item(form)

        form = self.bank.get_assessment_form_for_create([])
        form.display_name = 'assessment2'
        assessment2 = self.bank.create_assessment(form)
        self.bank.add_item(assessment2.ident, item2.ident)

        self.repo.add_asset(assessment2.ident, sequential2.ident)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'chapter'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['chapter']))
        form.set_children([sequential.ident])
        chapter = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'run'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['offering']))
        form.set_children([chapter.ident])
        form.set_sequestered(True)
        run = self.repo.create_composition(form)

        form = self.repo.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = 'test course'
        form.set_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['course']))
        form.set_children([run.ident])
        form.set_sequestered(True)
        return self.repo.create_composition(form)

    def setUp(self):
        super(EdXItemUnitTests, self).setUp()
        self.login()
        self.repo = self.create_new_user_repo()
        self.repo_id = unquote(str(self.repo.ident))
        am = gutils.get_session_data(self.req, 'am')
        self.bank = am.get_bank(self.repo.ident)

    def tearDown(self):
        super(EdXItemUnitTests, self).tearDown()

    def test_can_query_descendant_compositions_for_items(self):
        # create course composition, then run, then chapter, then sequential
        # query that the sequential is found when querying descendants of run
        course_composition = self.set_up_user_course()

        querier = self.bank.get_item_query()
        querier.match_composition_descendants(course_composition.ident, self.repo.ident, True)
        matches = self.bank.get_items_by_query(querier)
        self.assertEqual(
            matches.available(),
            1
        )
        self.assertEqual(
            matches.next().display_name.text,
            'item'
        )


class RepositoryChildrenTests(RepositoryTestCase):
    """Test the views for repository crud

    """
    def setUp(self):
        super(RepositoryChildrenTests, self).setUp()
        self.login()
        self.url = self.base_url + 'repository/repositories/'
        self.repo1 = self.create_new_repo()
        self.repo2 = self.create_new_repo()
        self.repo3 = self.create_new_repo()

        rm = gutils.get_session_data(self.req, 'rm')
        rm.add_child_repository(self.repo1.ident, self.repo2.ident)

        self.url = self.base_url + 'repository/repositories/'

    def tearDown(self):
        super(RepositoryChildrenTests, self).tearDown()

    def test_can_get_children(self):
        self.url += str(self.repo1.ident) + '/children/'
        req = self.client.get(self.url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(self.repo2.ident)
        )

    def test_can_update_children_list(self):
        self.url += str(self.repo1.ident) + '/children/'
        payload = {
            'childIds': [str(self.repo3.ident)]
        }
        req = self.client.put(self.url,
                              data=payload,
                              format='json')
        self.updated(req)

        req = self.client.get(self.url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['data']['count'],
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(self.repo3.ident)
        )


class RepositorySearchTests(AssessmentTestCase, RepositoryTestCase):
    """Test the views for repository search and pagination

    """
    def setUp(self):
        super(RepositorySearchTests, self).setUp()
        self.login()
        self.repo = self.create_new_repo()
        course_repo = self.create_new_course_repo()
        run_repo = self.create_new_run_repo()

        rm = gutils.get_session_data(self.req, 'rm')
        rm.add_child_repository(self.repo.ident, course_repo.ident)
        rm.add_child_repository(course_repo.ident, run_repo.ident)

        self.url = self.base_url + 'repository/repositories/' + str(self.repo.ident) + '/search/?'

        for i in range(0, 10):
            self.setup_asset(run_repo.ident)

        for i in range(0, 10):
            self.setup_composition(run_repo.ident)

        run_bank = self.get_bank(run_repo.ident)

        for i in range(0, 10):
            self.create_item(run_bank)

    def tearDown(self):
        super(RepositorySearchTests, self).tearDown()

    def test_page_limits_are_in_assets_only(self):
        url = self.url + 'page=1&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        first_page_ids = []
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Asset'
            )
            first_page_ids.append(obj['id'])

        url = self.url + 'page=2&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Asset'
            )
            self.assertNotIn(
                obj['id'],
                first_page_ids
            )

    def test_page_limits_are_in_compositions_only(self):
        url = self.url + 'page=3&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        first_page_ids = []
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Composition'
            )
            first_page_ids.append(obj['id'])

        url = self.url + 'page=4&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Composition'
            )
            self.assertNotIn(
                obj['id'],
                first_page_ids
            )

    def test_page_limits_are_in_items_only(self):
        url = self.url + 'page=5&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        first_page_ids = []
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Item'
            )
            first_page_ids.append(obj['id'])

        url = self.url + 'page=6&limit=5'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            5
        )
        for obj in data['objects']:
            self.assertEqual(
                obj['type'],
                'Item'
            )
            self.assertNotIn(
                obj['id'],
                first_page_ids
            )

    def test_page_limits_cross_assets_and_compositions(self):
        url = self.url + 'page=2&limit=7'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            7
        )
        for index, obj in enumerate(data['objects']):
            if index in [0, 1, 2]:
                self.assertEqual(
                    obj['type'],
                    'Asset'
                )
            else:
                self.assertEqual(
                    obj['type'],
                    'Composition'
                )

    def test_page_limits_cross_assets_compositions_and_items(self):
        url = self.url + 'page=1&limit=30'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            30
        )
        for index, obj in enumerate(data['objects']):
            if index in range(0, 10):
                self.assertEqual(
                    obj['type'],
                    'Asset'
                )
            elif index in range(10, 20):
                self.assertEqual(
                    obj['type'],
                    'Composition'
                )
            else:
                self.assertEqual(
                    obj['type'],
                    'Item'
                )

    def test_page_limits_cross_compositions_and_items(self):
        url = self.url + 'page=2&limit=15'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            15
        )
        for index, obj in enumerate(data['objects']):
            if index in range(0, 5):
                self.assertEqual(
                    obj['type'],
                    'Composition'
                )
            else:
                self.assertEqual(
                    obj['type'],
                    'Item'
                )

    def test_page_limits_exceed_number_of_total_objects(self):
        url = self.url + 'page=1&limit=50'
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['objects']),
            30
        )
        for index, obj in enumerate(data['objects']):
            if index in range(0, 10):
                self.assertEqual(
                    obj['type'],
                    'Asset'
                )
            elif index in range(10, 20):
                self.assertEqual(
                    obj['type'],
                    'Composition'
                )
            else:
                self.assertEqual(
                    obj['type'],
                    'Item'
                )


@override_settings(CELERY_ALWAYS_EAGER=True,
                   WEBSOCKET_EXCHANGE='test.backstage.producer')
class RepositoryCrUDTests(AssessmentTestCase, RepositoryTestCase):
    """Test the views for repository crud

    """
    def setUp(self):
        super(RepositoryCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.assessment_bank = self.create_assessment_bank()
        self.bad_repo_id = 'assessment.Bank%3A55203f0be7dde0815228bb41%40EDX.ORG'
        self.login()
        self.url = self.base_url + 'repository/repositories/'

        self.demo_course = open(ABS_PATH + '/producer/tests/files/content-mit-1805x-master.zip', 'rb')
        self.non_course = open(ABS_PATH + '/repository/tests/files/Flexure_structure_with_hints.pdf', 'rb')

    def tearDown(self):
        super(RepositoryCrUDTests, self).tearDown()
        self.demo_course.close()
        self.non_course.close()

    def test_can_create_new_course_repository(self):
        payload = {
            'displayName': 'my new repository',
            'description': 'for testing with',
            'genusTypeId': 'repository-genus-type%3Acourse-repo%40ODL.MIT.EDU'
        }
        req = self.client.post(self.url,
                               data=payload,
                               format='json')
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            repo['description']['text'],
            payload['description']
        )

        self.assertEqual(
            repo['genusTypeId'],
            payload['genusTypeId']
        )

    def test_can_create_new_course_run_repository(self):
        course = self.create_new_course_repo()
        payload = {
            'displayName': 'my new repository',
            'description': 'for testing with',
            'genusTypeId': 'repository-genus-type%3Acourse-run-repo%40ODL.MIT.EDU',
            'parentId': str(course.ident)
        }
        req = self.client.post(self.url,
                               data=payload,
                               format='json')
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            repo['description']['text'],
            payload['description']
        )
        self.assertEqual(
            repo['genusTypeId'],
            payload['genusTypeId']
        )


    def test_creating_course_run_repository_requires_parent_id(self):
        payload = {
            'displayName': 'my new repository',
            'description': 'for testing with',
            'genusTypeId': 'repository-genus-type%3Acourse-run-repo%40ODL.MIT.EDU'
        }
        req = self.client.post(self.url,
                               data=payload,
                               format='json')
        self.code(req, 500)

    def test_can_create_orchestrated_repository_with_default_attributes(self):
        payload = {
            'bankId': str(self.assessment_bank.ident)
        }
        req = self.client.post(self.url, payload)
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
            self.assessment_bank.ident.identifier,
            Id(repo['id']).identifier
        )

    def test_can_create_orchestrated_repository_and_set_attributes(self):
        payload = {
            'bankId': str(self.assessment_bank.ident),
            'displayName': 'my new orchestra',
            'description': 'for my assessment bank'
        }
        req = self.client.post(self.url, payload)
        self.created(req)
        repo = self.json(req)
        self.assertEqual(
            repo['displayName']['text'],
            payload['displayName']
        )
        self.assertEqual(
            repo['description']['text'],
            payload['description']
        )
        self.assertEqual(
            self.assessment_bank.ident.identifier,
            Id(repo['id']).identifier
        )

    def test_missing_parameters_throws_exception_on_create(self):
        self.num_repos(0)

        basic_payload = {
            'displayName': 'my new repository',
            'description': 'for testing with'
        }
        blacklist = ['displayName', 'description']

        for item in blacklist:
            payload = deepcopy(basic_payload)
            del payload[item]
            req = self.client.post(self.url, payload)
            self.code(req, 500)
            self.message(req,
                         '\\"' + item + '\\" required in input parameters but not provided.')

        self.num_repos(0)

    def test_can_get_repository_details(self):
        repo = self.create_new_repo()
        url = self.url + unquote(str(repo.ident))
        req = self.client.get(url)
        self.ok(req)
        repo_details = self.json(req)
        for attr, val in repo.object_map.iteritems():
            self.assertEqual(
                val,
                repo_details[attr]
            )
        self.message(req, '"assets":')

    def test_invalid_repository_id_throws_exception(self):
        self.create_new_repo()
        url = self.url + 'x'
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Invalid ID.')

    def test_bad_repository_id_throws_exception(self):
        self.create_new_repo()
        url = self.url + self.bad_repo_id
        req = self.client.get(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

    def test_can_delete_repository(self):
        self.num_repos(0)

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + unquote(str(repo.ident))
        req = self.client.delete(url)
        self.deleted(req)

        self.num_repos(0)

    def test_trying_to_delete_repository_with_assets_throws_exception(self):
        self.num_repos(0)

        repo = self.create_new_repo()

        self.num_repos(1)
        self.setup_asset(repo.ident)

        url = self.url + unquote(str(repo.ident))
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Repository is not empty.')

        self.num_repos(1)

    def test_trying_to_delete_repository_with_invalid_id_throws_exception(self):
        self.num_repos(0)

        self.create_new_repo()

        self.num_repos(1)

        url = self.url + self.bad_repo_id
        req = self.client.delete(url)
        self.code(req, 500)
        self.message(req, 'Object not found.')

        self.num_repos(1)

    def test_can_update_repository(self):
        self.num_repos(0)

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + unquote(str(repo.ident))

        test_cases = [('displayName', 'a new name'),
                      ('description', 'foobar')]
        for case in test_cases:
            payload = {
                case[0]: case[1]
            }
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            updated_repo = self.json(req)
            self.assertEqual(
                updated_repo[case[0]]['text'],
                case[1]
            )

        self.num_repos(1)

    def test_update_with_invalid_id_throws_exception(self):
        self.num_repos(0)

        self.create_new_repo()

        self.num_repos(1)

        url = self.url + self.bad_repo_id

        test_cases = [('displayName', 'a new name'),
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

        repo = self.create_new_repo()

        self.num_repos(1)

        url = self.url + unquote(str(repo.ident))

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
                         '[\\"displayName\\", \\"description\\", \\"childIds\\"]')

        self.num_repos(1)
        req = self.client.get(url)
        repo_fresh = self.json(req)

        params_to_test = ['id', 'displayName', 'description']
        repo_map = repo.object_map
        for param in params_to_test:
            if param == 'id':
                expected = repo_map[param]
                returned = repo_fresh[param]
            else:
                expected = repo_map[param]['text']
                returned = repo_fresh[param]['text']
            self.assertEqual(
                expected,
                returned
            )

    def test_student_can_view_repositories(self):
        self.create_new_repo()
        self.login(non_instructor=True)
        self.num_repos(1)

        url = self.url
        req = self.client.get(url)
        self.ok(req)

    def test_can_upload_new_course_to_domain_repo(self):
        domain = self.create_new_repo()
        self.num_repos(1)
        url = self.url + str(domain.ident) + '/upload/'
        payload = {
            'myFile': self.demo_course
        }
        req = self.client.post(url, data=payload)
        self.ok(req)
        self.num_repos(5)  # Users, user-repo, course, run, and domain
        rm = gutils.get_session_data(self.req, 'rm')
        querier = rm.get_repository_query()
        querier.match_genus_type(Type(**REPOSITORY_GENUS_TYPES['course-repo']), True)
        course_repos = rm.get_repositories_by_query(querier)
        self.assertEqual(
            course_repos.available(),
            1
        )
        querier = rm.get_repository_query()
        querier.match_genus_type(Type(**REPOSITORY_GENUS_TYPES['course-run-repo']), True)
        run_repos = rm.get_repositories_by_query(querier)
        self.assertEqual(
            run_repos.available(),
            1
        )

    def test_can_upload_new_course_to_user_repo(self):
        user_repo = self.create_new_user_repo()
        self.num_repos(1)  # my test non-domain, target repo
        url = self.url + str(user_repo.ident) + '/upload/'
        payload = {
            'myFile': self.demo_course
        }
        req = self.client.post(url, data=payload)
        self.ok(req)
        self.num_repos(5)  # Users, user-repo, target repo, course repo, run repo
        rm = gutils.get_session_data(self.req, 'rm')
        querier = rm.get_repository_query()
        querier.match_genus_type(Type(**REPOSITORY_GENUS_TYPES['course-run-repo']), True)
        course_run_repos = rm.get_repositories_by_query(querier)
        self.assertEqual(
            course_run_repos.available(),
            1
        )
        course_run_repo = course_run_repos.next()
        course_run_repo = rm.get_repository(course_run_repo.ident)
        self.num_compositions(87, repo=course_run_repo)  # are these numbers accurate?
        self.num_compositions(278, repo=course_run_repo, unsequestered=True)  # are these numbers accurate?

        course_run_repo.use_unsequestered_composition_view()

        querier = course_run_repo.get_composition_query()
        querier.match_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['course']), True)
        course_compositions = course_run_repo.get_compositions_by_query(querier)
        self.assertEqual(
            course_compositions.available(),
            1
        )

        querier = course_run_repo.get_composition_query()
        querier.match_genus_type(Type(**EDX_COMPOSITION_GENUS_TYPES['offering']), True)
        run_compositions = course_run_repo.get_compositions_by_query(querier)
        self.assertEqual(
            run_compositions.available(),
            0
        )

    def test_bad_file_upload_throws_exception(self):
        domain = self.create_new_repo()
        self.num_repos(1)
        url = self.url + str(domain.ident) + '/upload/'
        payload = {
            'myFile': self.non_course
        }
        req = self.client.post(url, data=payload)
        self.ok(req)
        self.num_repos(1)

