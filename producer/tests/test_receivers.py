"""without an async listener, no way to check that the message was
received properly. But we can at least make sure no exceptions thrown"""

import unittest

from django.test.utils import override_settings
from dlkit.runtime.proxy_example import SimpleRequest

from utilities.testing import DjangoTestCase

from ..receivers import RabbitMQReceiver

@override_settings(WEBSOCKET_EXCHANGE='test.backstage.producer')
class RabbitMQReceiverTest(DjangoTestCase):
    def setUp(self):
        super(RabbitMQReceiverTest, self).setUp()

        req = SimpleRequest(username='cjshaw@mit.edu')
        self.mq = RabbitMQReceiver(req)

    def tearDown(self):
        super(RabbitMQReceiverTest, self).tearDown()

    @unittest.skip('RabbitMQ does not work in test environment')
    def test_can_emit_new_resources(self):
        self.mq.new_resources('123', ['id'])

    @unittest.skip('RabbitMQ does not work in test environment')
    def test_can_emit_new_items(self):
        self.mq.new_items('456', ['id'])

