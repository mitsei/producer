import boto
import envoy

from assessments.tests.test_views import AssessmentTestCase

from boto.s3.key import Key

from copy import deepcopy

from dlkit.mongo.records.types import COMPOSITION_RECORD_TYPES, EDX_COMPOSITION_GENUS_TYPES

from dlkit_django.primordium import Id, DataInputStream, Type

from django.conf import settings
from django.utils.http import unquote

from utilities import general as gutils
from utilities.testing import DjangoTestCase, ABS_PATH


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
        return rm.create_repository(form)

    def get_asset(self, asset_id):
        return self.repo.get_asset(Id(asset_id))

    def get_repo(self, repo_id):
        if not isinstance(repo_id, Id):
            repo_id = Id(repo_id)
        rm = gutils.get_session_data(self.req, 'rm')
        return rm.get_repository(repo_id)

    def num_assets(self, val):
        self.assertEqual(
            self.get_repo(self.repo.ident).get_assets().available(),
            val
        )

    def num_compositions(self, val):
        self.assertEqual(
            self.get_repo(self.repo.ident).get_compositions().available(),
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

    def setup_asset(self, repository_id):
        if not isinstance(repository_id, Id):
            repository_id = Id(repository_id)

        test_file = '/repository/tests/files/Flexure_structure_with_hints.pdf'

        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(repository_id)
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

        self.default_asset_file = ABS_PATH + test_file
        with open(self.default_asset_file, 'r') as file_:
            asset_content_form.set_data(DataInputStream(file_))

        repo.create_asset_content(asset_content_form)

        new_asset = repo.get_asset(new_asset.ident)
        return new_asset

    def setup_composition(self, repository_id):
        rm = gutils.get_session_data(self.req, 'rm')
        repo = rm.get_repository(Id(repository_id))

        new_asset = self.setup_asset(repository_id)

        form = repo.get_composition_form_for_create([])
        form.display_name = 'my test composition'
        form.description = 'foobar'
        form.set_children([new_asset.ident])
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

    def test_can_delete_composition(self):
        self.num_compositions(0)
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1)

        url = self.url + unquote(str(composition.ident))
        req = self.client.delete(url)
        self.deleted(req)
        self.num_compositions(0)

    def test_can_get_composition_details(self):
        new_composition = self.setup_composition(self.repo_id)
        url = self.url + unquote(str(new_composition.ident))

        req = self.client.get(url)
        self.ok(req)
        composition = self.json(req)
        self.assertEqual(
            len(composition['childIds']),
            1
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
        composition = self.setup_composition(self.repo_id)
        url = self.url + unquote(str(composition.ident))

        test_cases = [{'displayName': 'ha'},
                      {'description': 'funny'}]

        for payload in test_cases:
            req = self.client.put(url, payload, format='json')
            self.updated(req)
            data = self.json(req)
            key = payload.keys()[0]
            self.assertEqual(
                data[key]['text'],
                payload[key]
            )

    def test_updating_child_ids_removes_previous_ones(self):
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1)
        url = self.url + unquote(str(composition.ident))

        # get the original asset id
        req = self.client.get(url)
        data = self.json(req)
        old_asset_id = data['childIds'][0]

        new_asset = self.setup_asset(self.repo_id)

        payload = {
            'childIds': str(new_asset.ident)
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            str(new_asset.ident)
        )
        self.assertEqual(
            data['childIds'],
            [str(new_asset.ident)]
        )
        self.num_compositions(1)

    def test_updating_child_ids_preserves_order(self):
        composition = self.setup_composition(self.repo_id)
        self.num_compositions(1)
        url = self.url + unquote(str(composition.ident))

        # get the original asset id
        req = self.client.get(url)
        data = self.json(req)
        old_asset_id = data['childIds'][0]

        new_asset = self.setup_asset(self.repo_id)

        payload = {
            'childIds': [old_asset_id, str(new_asset.ident)]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            str(new_asset.ident)
        )
        self.assertEqual(
            data['childIds'],
            [old_asset_id, str(new_asset.ident)]
        )
        self.num_compositions(1)

        payload = {
            'childIds': [str(new_asset.ident), old_asset_id]
        }

        req = self.client.put(url, payload, format='json')
        self.updated(req)
        data = self.json(req)
        self.assertNotEqual(
            old_asset_id,
            str(new_asset.ident)
        )
        self.assertEqual(
            data['childIds'],
            [str(new_asset.ident), old_asset_id]
        )
        self.num_compositions(1)

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
        self.num_assets(1)

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

        self.num_assets(2)

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
        self.num_assets(2)

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
            'genusTypeId': 'edx-composition%3Acourse%40EDX.ORG',
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
            str(Type(**EDX_COMPOSITION_GENUS_TYPES['course']))
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
        url = self.url

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'repositoryId': str(self.repo.ident)
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition = self.json(req)

        payload = {
            'displayName': 'test composition',
            'description': 'for testing',
            'childIds': [composition['id']],
            'repositoryId': str(self.repo.ident),
            'genusTypeId': 'edx-composition%3Achapter%40EDX.ORG',
        }

        req = self.client.post(url, payload, format='json')
        self.created(req)
        composition2 = self.json(req)

        url = self.base_url + 'repository/repositories/' + str(self.repo.ident) + '/compositions/?nested'
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

    def tearDown(self):
        super(RepositoryCrUDTests, self).tearDown()

    def test_can_create_new_repository(self):
        payload = {
            'displayName': 'my new repository',
            'description': 'for testing with'
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
                         '[\\"displayName\\", \\"description\\"]')

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
