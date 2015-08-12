"""without an async listener, no way to check that the message was
received properly. But we can at least make sure no exceptions thrown"""

import pika

from django.test.utils import override_settings
from dlkit_django.proxy_example import TestRequest

from utilities.testing import DjangoTestCase

from ..receivers import RabbitMQReceiver

@override_settings(WEBSOCKET_EXCHANGE='test.backstage.producer')
class RabbitMQReceiverTest(DjangoTestCase):
    def setUp(self):
        super(RabbitMQReceiverTest, self).setUp()

        req = TestRequest(username='cjshaw@mit.edu')
        self.mq = RabbitMQReceiver(req)

    def tearDown(self):
        super(RabbitMQReceiverTest, self).tearDown()

    def test_can_emit_new_resources(self):
        self.mq.new_resources(['id'])

    def test_can_emit_new_items(self):
        self.mq.new_items(['id'])

