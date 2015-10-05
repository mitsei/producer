from django.utils.http import unquote

from utilities import general as gutils
from utilities.testing import DjangoTestCase

from dlkit_django.primordium import Id


class LearningTestCase(DjangoTestCase):
    """
    """
    def setUp(self):
        super(LearningTestCase, self).setUp()
        self.url = self.base_url + 'learning/'

    def tearDown(self):
        super(LearningTestCase, self).tearDown()


class BasicServiceTests(LearningTestCase):
    """Test the basic behavior

    """
    def setUp(self):
        super(BasicServiceTests, self).setUp()

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_unauthenticated_users_cannot_access(self):
        banks = self.url + 'banks'
        req = self.client.get(banks)
        self.code(req, 403)


class ObjectivesCrUDTests(LearningTestCase):
    """Test the views for objectives

    """
    def setUp(self):
        super(ObjectivesCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.objectives = self.url + 'objectives'
        self.login()

    def tearDown(self):
        super(ObjectivesCrUDTests, self).tearDown()

    def test_can_get_objectives(self):
        req = self.client.get(self.objectives)
        self.ok(req)

    def test_objectives_are_from_multiple_banks(self):
        req = self.client.get(self.objectives + '?page=all')
        data = self.json(req)
        self.assertTrue(data['data']['count'] > 10)
        self.assertTrue(data['data']['next'] is None)
        self.assertTrue(data['data']['previous'] is None)

        first_bank_id = data['data']['results'][0]['objectiveBankId']

        only_one_bank = True

        for obj in data['data']['results']:
            if obj['objectiveBankId'] != first_bank_id:
                only_one_bank = False
                break

        self.assertFalse(only_one_bank)

    def test_only_outcomes_returned(self):
        req = self.client.get(self.objectives + '?page=all')
        data = self.json(req)

        for obj in data['data']['results']:
            self.assertEqual(
                obj['genusTypeId'],
                'mc3-objective%3Amc3.learning.outcome%40MIT-OEIT'
            )
