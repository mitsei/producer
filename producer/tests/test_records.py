import json

from dlkit.mongo.records.types import COMPOSITION_RECORD_TYPES
from dlkit.primordium.type.primitives import Type
from dlkit_django.proxy_example import User

from dysonx.dysonx import get_or_create_user_repo, _get_genus_type

from repository.tests.test_views import RepositoryTestCase

from utilities import general as gutils

EDX_COMPOSITION = Type(**COMPOSITION_RECORD_TYPES['edx-composition'])


class CompositionRecordTests(RepositoryTestCase):
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

    def tearDown(self):
        super(CompositionRecordTests, self).tearDown()

    def test_can_get_split_test_child_ids(self):
        updated_split_test = self.user_repo.get_composition(self.split_test.ident)
        child_ids = updated_split_test.group_id_to_child

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

