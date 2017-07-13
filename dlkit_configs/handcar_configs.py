"""configs specific to the MC3 Handcar learning objective service"""
#pylint: disable=import-error
#  dlkit_runtime_project used as scaffold for testing
try:
    from django.conf import settings
except ImportError:
    from ..dlkit_runtime_project import settings

from .utilities import impl_key_dict

HANDCAR_MC3 = {
    'id': 'handcar_mc3',
    'displayName': 'Handcar MC3 Configuration',
    'description': 'Configuration for Handcar MC3 Production Service',
    'parameters': {
        'implKey': impl_key_dict('handcar'),
        'hostName': {
            'syntax': 'STRING',
            'displayName': 'Host Name',
            'description': 'Host Name for Handcar RESTFul Service Provider',
            'values': [
                {'value': 'mc3.mit.edu', 'priority': 1}
            ]
        },
        'appKey': {
            'syntax': 'STRING',
            'displayName': 'App Key',
            'description': 'Agent Key for Handcar service provider',
            'values': [
                {'value': settings.MC3_HANDCAR_APP_KEY, 'priority': 1}
            ]
        }
    }
}


HANDCAR_MC3_DEMO = {
    'id': 'handcar_mc3',
    'displayName': 'Handcar MC3 Demo Configuration',
    'description': 'Configuration for Handcar MC3 Demo Service',
    'parameters': {
        'implKey': impl_key_dict('handcar'),
        'hostName': {
            'syntax': 'STRING',
            'displayName': 'Host Name',
            'description': 'Host Name for Handcar RESTFul Service Provider',
            'values': [
                {'value': 'mc3-demo.mit.edu', 'priority': 1}
            ]
        },
        'appKey': {
            'syntax': 'STRING',
            'displayName': 'App Key',
            'description': 'Agent Key for Handcar service provider',
            'values': [
                {'value': settings.MC3_DEMO_HANDCAR_APP_KEY, 'priority': 1}
            ]
        }
    }
}

HANDCAR_MC3_DEV = {
    'id': 'handcar_mc3',
    'displayName': 'Handcar MC3 Dev Configuration',
    'description': 'Configuration for Handcar MC3 Dev Service',
    'parameters': {
        'implKey': impl_key_dict('handcar'),
        'hostName': {
            'syntax': 'STRING',
            'displayName': 'Host Name',
            'description': 'Host Name for Handcar RESTFul Service Provider',
            'values': [
                {'value': 'mc3-dev.mit.edu', 'priority': 1}
            ]
        },
        'appKey': {
            'syntax': 'STRING',
            'displayName': 'App Key',
            'description': 'Agent Key for Handcar service provider',
            'values': [
                {'value': settings.MC3_DEV_HANDCAR_APP_KEY, 'priority': 1}
            ]
        }
    }
}
