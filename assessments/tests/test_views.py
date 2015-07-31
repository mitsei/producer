from django.utils.http import unquote

from utilities import general as gutils
from utilities.testing import DjangoTestCase

from dlkit_django.primordium import Id


class AssessmentTestCase(DjangoTestCase):
    """
    """
    def create_assessment_bank(self):
        am = gutils.get_session_data(self.req, 'am')
        form = am.get_bank_form_for_create([])
        form.display_name = 'foo'
        form.description = 'bar'
        return am.create_bank(form)

    def create_item(self, bank):
        form = bank.get_item_form_for_create([])
        form.display_name = 'a test item!'
        form.description = 'for testing with'

        self._lo = 'foo@bar:baz'

        form.set_learning_objectives([Id(self._lo)])
        new_item = bank.create_item(form)

        question_form = bank.get_question_form_for_create(new_item.ident, [])
        question_form.display_name = 'Question for ' + new_item.display_name.text
        question_form.description = ''
        bank.create_question(question_form)

        answer_form = bank.get_answer_form_for_create(new_item.ident, [])
        answer_form.display_name = 'Answer for ' + new_item.display_name.text
        bank.create_answer(answer_form)

        item = bank.get_item(new_item.ident)

        return item

    def setUp(self):
        super(AssessmentTestCase, self).setUp()
        self.url += 'assessment/'

    def setup_assessment(self):
        am = gutils.get_session_data(self.req, 'am')
        bank = am.get_bank(Id(self.gradebook['id']))

        item_form = bank.get_item_form_for_create([])
        item_form.display_name = 'test item'
        item_form.description = 'for testing'
        item = bank.create_item(item_form)

        assessment_form = bank.get_assessment_form_for_create([])
        assessment_form.display_name = 'an assessment'
        assessment_form.description = 'for testing'
        assessment = bank.create_assessment(assessment_form)

        bank.add_item(assessment.ident, item.ident)

        offered_form = bank.get_assessment_offered_form_for_create(assessment.ident, [])
        offered = bank.create_assessment_offered(offered_form)

        taken_form = bank.get_assessment_taken_form_for_create(offered.ident, [])
        taken = bank.create_assessment_taken(taken_form)

        return taken.object_map

    def tearDown(self):
        super(AssessmentTestCase, self).tearDown()


class BasicServiceTests(AssessmentTestCase):
    """Test the basic behavior

    """
    def num_banks(self, val):
        am = gutils.get_session_data(self.req, 'am')

        self.assertEqual(
            am.banks.available(),
            val
        )

    def setUp(self):
        super(BasicServiceTests, self).setUp()

    def tearDown(self):
        super(BasicServiceTests, self).tearDown()

    def test_unauthenticated_users_cannot_access(self):
        banks = self.url + 'banks'
        req = self.client.get(banks)
        self.code(req, 403)


class AssessmentBankCrUDTests(AssessmentTestCase):
    """Test the views for assessment bank crud

    """
    def num_banks(self, val):
        am = gutils.get_session_data(self.req, 'am')

        self.assertEqual(
            am.banks.available(),
            val
        )

    def setUp(self):
        super(AssessmentBankCrUDTests, self).setUp()

        self.login()
        self.banks = self.url + 'banks'

    def tearDown(self):
        super(AssessmentBankCrUDTests, self).tearDown()

    def test_can_get_assessment_banks(self):
        bank = self.create_assessment_bank()
        req = self.client.get(self.banks)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(bank.ident)
        )

    def test_can_create_assessment_bank(self):
        self.num_banks(0)
        payload = {
            "displayName": "a bank",
            "description": "for testing"
        }
        req = self.client.post(self.banks,
                               data=payload,
                               format='json')
        self.created(req)
        data = self.json(req)

        for attr in ['displayName', 'description']:
            self.assertEqual(
                data[attr]['text'],
                payload[attr]
            )

        self.num_banks(1)

    def test_can_get_individual_bank_details(self):
        bank = self.create_assessment_bank()
        url = '{0}/{1}'.format(self.banks,
                               unquote(str(bank.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            data['id'],
            str(bank.ident)
        )

    def test_can_update_bank(self):
        bank = self.create_assessment_bank()
        url = '{0}/{1}'.format(self.banks,
                               unquote(str(bank.ident)))

        payload = {
            "displayName": "a second name"
        }

        req = self.client.put(url,
                              data=payload,
                              format='json')

        self.updated(req)
        data = self.json(req)
        self.assertEqual(
            data['id'],
            str(bank.ident)
        )
        self.assertEqual(
            data['displayName']['text'],
            payload['displayName']
        )

    def test_can_delete_bank(self):
        bank = self.create_assessment_bank()
        self.num_banks(1)
        url = '{0}/{1}'.format(self.banks,
                               unquote(str(bank.ident)))

        req = self.client.delete(url)
        self.deleted(req)
        self.num_banks(0)


class AssessmentItemCrUDTests(AssessmentTestCase):
    """Test the views for assessment items

    """
    def num_items(self, val):
        self.assertEqual(
            self.bank.items.available(),
            val
        )

    def setUp(self):
        super(AssessmentItemCrUDTests, self).setUp()
        # also need a test assessment bank here to do orchestration with
        self.bank = self.create_assessment_bank()
        self.items = self.url + 'items'
        self.login()

    def tearDown(self):
        super(AssessmentItemCrUDTests, self).tearDown()

    def test_can_create_item(self):
        self.num_items(0)
        payload = {
            "bankId": str(self.bank.ident),
            "displayName": "a bank",
            "description": "for testing"
        }
        req = self.client.post(self.items,
                               data=payload,
                               format='json')
        self.created(req)
        data = self.json(req)

        for attr in ['displayName', 'description']:
            self.assertEqual(
                data[attr]['text'],
                payload[attr]
            )

        self.num_items(1)

    def test_can_get_items_list(self):
        item = self.create_item(self.bank)
        req = self.client.get(self.items)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(item.ident)
        )

    def test_can_get_individual_item_details(self):
        item = self.create_item(self.bank)
        url = '{0}/{1}'.format(self.items,
                               unquote(str(item.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)

        self.assertEqual(
            data['id'],
            str(item.ident)
        )

    def test_can_delete_item(self):
        item = self.create_item(self.bank)
        self.num_items(1)
        url = '{0}/{1}'.format(self.items,
                               unquote(str(item.ident)))
        req = self.client.delete(url)
        self.deleted(req)
        self.num_items(0)

    def test_can_update_item(self):
        item = self.create_item(self.bank)
        url = '{0}/{1}'.format(self.items,
                               unquote(str(item.ident)))

        payload = {
            "displayName": "a new name"
        }

        req = self.client.put(url,
                              data=payload,
                              format='json')
        self.updated(req)
        data = self.json(req)

        self.assertEqual(
            data['displayName']['text'],
            payload['displayName']
        )

    def test_can_get_bank_items(self):
        item = self.create_item(self.bank)
        url = '{0}banks/{1}/items'.format(self.url,
                                           unquote(str(self.bank.ident)))
        req = self.client.get(url)
        self.ok(req)
        data = self.json(req)
        self.assertEqual(
            len(data['data']['results']),
            1
        )
        self.assertEqual(
            data['data']['results'][0]['id'],
            str(item.ident)
        )
