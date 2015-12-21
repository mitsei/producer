import json

from records.registry import COMPOSITION_RECORD_TYPES, OSID_OBJECT_RECORD_TYPES
from dlkit.primordium.type.primitives import Type
from dlkit_django.proxy_example import User

from dysonx.dysonx import get_or_create_user_repo, _get_genus_type, get_enclosed_object_asset

from assessments.tests.test_views import AssessmentTestCase
from repository.tests.test_views import RepositoryTestCase

from utilities import general as gutils

EDX_COMPOSITION = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])
ENCLOSURE = Type(**OSID_OBJECT_RECORD_TYPES['enclosure'])


class CompositionRecordTests(AssessmentTestCase, RepositoryTestCase):
    """Test composition records

    """
    def create_composition(self, repository, genus_type, name="new comp", parent=None):
        genus = _get_genus_type(genus_type)
        form = repository.get_composition_form_for_create([EDX_COMPOSITION])
        form.display_name = name
        form.description = 'for testing'
        form.set_genus_type(genus)

        if genus_type == 'course':
            form.set_org('MITx')

        composition = repository.create_composition(form)

        if parent is not None:
            updated_parent = repository.get_composition(parent.ident)
            form = repository.get_composition_form_for_update(parent.ident)
            current_children_ids = list(updated_parent.get_child_ids())
            current_children_ids.append(composition.ident)
            form.set_children(current_children_ids)
            repository.update_composition(form)

        return composition

    def setUp(self):
        super(CompositionRecordTests, self).setUp()
        self.rm = gutils.get_session_data(self.req, 'rm')

        self.user = User(username='cjshaw@mit.edu', authenticated=True)
        self.user_repo = get_or_create_user_repo(self.user.username)

        self.user2 = User(username='foo@mit.edu', authenticated=True)
        self.user2_repo = get_or_create_user_repo(self.user2.username)

        self.course = self.create_composition(self.user_repo, 'course', name='NP101')

        self.split_test = self.create_composition(self.user_repo, 'split_test', parent=self.course)
        self.child1 = self.create_composition(self.user_repo,
                                              'sequential',
                                              name='test sequential',
                                              parent=self.split_test)
        self.child2 = self.create_composition(self.user_repo,
                                              'vertical',
                                              name='test vertical',
                                              parent=self.split_test)

        self.split_test = self.user_repo.get_composition(self.split_test.ident)

    def tearDown(self):
        super(CompositionRecordTests, self).tearDown()

    def test_can_get_split_test_child_ids(self):
        child_ids = self.split_test.group_id_to_child

        expected = {
            '0': 'i4x://MITx/NP101/sequential/test-sequential',
            '1': 'i4x://MITx/NP101/vertical/test-vertical'
        }
        returned = json.loads(child_ids.replace('&quot;', '"'))

        for key in returned:
            self.assertEqual(
                returned[key],
                expected[key]
            )

    def test_can_clone_composition_to_new_repo(self):
        self.num_compositions(4, self.user_repo)
        self.num_compositions(0, self.user2_repo)

        new_split_test = self.split_test.clone_to(self.user2_repo)

        self.num_compositions(4, self.user_repo)
        self.num_compositions(1, self.user2_repo)

        self.assertNotEqual(
            str(new_split_test.ident),
            str(self.split_test.ident)
        )

        old_child_ids = [str(i) for i in self.split_test.get_child_ids()]

        self.assertEqual(
            new_split_test.get_child_ids().available(),
            2
        )

        for new_child_id in new_split_test.get_child_ids():
            self.assertIn(str(new_child_id), old_child_ids)

    def test_on_clone_assets_not_cloned(self):
        test_asset = self.setup_asset(self.user_repo.ident)
        self.user_repo.add_asset(test_asset.ident, self.child1.ident)

        self.num_assets(1, self.user_repo)
        self.num_assets(0, self.user2_repo)

        new_child = self.child1.clone_to(self.user2_repo)

        self.num_assets(1, self.user_repo)
        self.num_assets(0, self.user2_repo)

        self.assertNotEqual(
            str(new_child.ident),
            str(self.child1.ident)
        )

        new_asset = self.user2_repo.get_composition_assets(new_child.ident).next()

        self.assertEqual(
            str(test_asset.ident),
            str(new_asset.ident)
        )

    def test_can_clone_assets(self):
        test_asset = self.setup_asset(self.user_repo.ident)
        self.user_repo.add_asset(test_asset.ident, self.child1.ident)

        self.num_assets(1, self.user_repo)
        self.num_assets(0, self.user2_repo)

        new_asset = test_asset.clone_to(self.user2_repo)

        self.num_assets(1, self.user_repo)
        self.num_assets(1, self.user2_repo)

        self.assertNotEqual(
            str(new_asset.ident),
            str(test_asset.ident)
        )

    def test_cloning_enclosure_asset_also_clones_enclosed_object(self):
        am = gutils.get_session_data(self.req, 'am')
        user_bank = am.get_bank(self.user_repo.ident)
        user2_bank = am.get_bank(self.user2_repo.ident)

        test_item = self.create_item(user_bank)
        self.user_repo.add_asset(test_item.ident, self.child1.ident)
        test_asset = get_enclosed_object_asset(self.user_repo, test_item)

        self.num_assets(1, self.user_repo)
        self.num_assets(0, self.user2_repo)

        self.num_items(user_bank, 1)
        self.num_items(user2_bank, 0)

        new_asset = test_asset.clone_to(self.user2_repo)

        self.num_assets(1, self.user_repo)
        self.num_assets(1, self.user2_repo)

        self.num_items(user_bank, 1)
        self.num_items(user2_bank, 1)

        self.assertNotEqual(
            str(new_asset.ident),
            str(self.child1.ident)
        )

        self.assertTrue(new_asset.has_record_type(ENCLOSURE))

        old_enclosed_object = test_asset.get_enclosed_object()
        new_enclosed_object = new_asset.get_enclosed_object()

        self.assertNotEqual(
            str(old_enclosed_object.ident),
            str(new_enclosed_object.ident)
        )

        self.assertEqual(
            old_enclosed_object.display_name.text,
            new_enclosed_object.display_name.text
        )

        self.assertEqual(
            old_enclosed_object.description.text,
            new_enclosed_object.description.text
        )

        self.assertEqual(
            str(old_enclosed_object.object_map['learningObjectiveIds']),
            str(new_enclosed_object.object_map['learningObjectiveIds'])
        )

