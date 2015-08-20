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

    def _pub_wrapper(self, verb, obj_type='', notification_id=None, id_list=None, status=''):
        ids = [str(i) for i in id_list]
        message = {
            'data': ids,
            'id': str(notification_id),
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
                obj_type in ['assets', 'resources', 'items', 'banks', 'repositories']):

            def wrapper(*args, **kwargs):
                return self._pub_wrapper(verb, obj_type, args[0], args[1])
            return wrapper
        raise AttributeError


class SimpleAssetReceiver(object):
    """The asset receiver is the consumer supplied interface for receiving notifications pertaining to new, updated or deleted
        ``Asset`` objects."""

    def __init__(self):
        self._notifications = list()

    def new_assets(self, notification_id, asset_ids):
        """The callback for notifications of new assets.

        :param notification_id: the notification ``Id``
        :type notification_id: ``osid.id.Id``
        :param asset_ids: the ``Ids`` of the new ``Assets``
        :type asset_ids: ``osid.id.IdList``


        *compliance: mandatory -- This method must be implemented.*

        """
        self._notifications.append({str(notification_id): asset_ids})

    def changed_assets(self, notification_id, asset_ids):
        """The callback for notification of updated assets.

        :param notification_id: the notification ``Id``
        :type notification_id: ``osid.id.Id``
        :param asset_ids: the ``Ids`` of the updated ``Assets``
        :type asset_ids: ``osid.id.IdList``


        *compliance: mandatory -- This method must be implemented.*

        """
        self._notifications.append({str(notification_id): asset_ids})

    def deleted_assets(self, notification_id, asset_ids):
        """the callback for notification of deleted assets.

        :param notification_id: the notification ``Id``
        :type notification_id: ``osid.id.Id``
        :param asset_ids: the ``Ids`` of the deleted ``Assets``
        :type asset_ids: ``osid.id.IdList``


        *compliance: mandatory -- This method must be implemented.*

        """
        self._notifications.append({str(notification_id): asset_ids})
