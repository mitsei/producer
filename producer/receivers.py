"""Define the Notification receivers here"""
import json
import pika

from django.conf import settings


class RabbitMQReceiver(object):
    """receiver class that sends messages to RabbitMQ, on the app's channel"""

    def __init__(self, request):
        self.username = request.user.username
        self.exch = settings.WEBSOCKET_EXCHANGE or ''
        conn = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.ch = conn.channel()
        self.ch.exchange_declare(exchange=self.exch,
                                 type='fanout')
        super(RabbitMQReceiver, self).__init__()

    def _pub(self, data, routing_key=''):
        return self.ch.basic_publish(exchange=self.exch,
                                     routing_key=routing_key,
                                     body=json.dumps(data))

    def _pub_wrapper(self, verb, obj_type='', id_list=None, status=''):
        ids = [str(i) for i in id_list]
        message = {
            'data': ids,
            'objType': obj_type.lower(),
            'username': self.username,
            'verb': verb
        }
        if status != '':
            message.update({
                'status': status
            })
        return self._pub(message)

    # def new_resources(self, id_list):
    #     return self._pub_wrapper(id_list, 'new', 'resources')

    def __getattr__(self, item):
        verb = item.split('_')[0]
        obj_type = item.split('_')[-1]
        if (verb in ['new', 'changed', 'deleted'] and
                obj_type in ['resources', 'items', 'banks', 'repositories']):

            def wrapper(*args, **kwargs):
                return self._pub_wrapper(verb, obj_type, args[0])
            return wrapper
        raise AttributeError

