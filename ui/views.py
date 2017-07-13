from django.conf import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect, Http404

from dlkit.runtime.primitives import Type

from dysonx.dysonx import get_or_create_user_repo

from dlkit.records.registry import REPOSITORY_GENUS_TYPES

from utilities.general import log_error, activate_managers, get_session_data, extract_items


def check_credentials(request):
    username = request.POST['username']
    password = request.POST['password']
    redirect_url = request.POST['next']

    try:
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                if user.is_authenticated():
                    if not redirect_url or redirect_url == '':
                        redirect_url = '/dashboard/'
                    return HttpResponseRedirect(redirect_url)
                else:
                    raise AssertionError('Bad credentials provided.')
            else:
                raise AssertionError('Bad credentials provided.')
        else:
            raise AssertionError('Bad credentials provided.')
    except AssertionError as ex:
        return render_to_response('ui/login.html',
                                  {'state': ex.args[0]},
                                  RequestContext(request))
    except Exception as ex:
        msg = log_error('ui.views.check_credentials()', ex)
        return Http404(msg)

@login_required()
@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    """Dashboard for app
    Send list of domain repositories
    """
    privileges = ['admin', 'curate', 'author']
    user_repo = get_or_create_user_repo(request.user.username)
    return render_to_response('ui/dashboard.html',
                              {
                                  'enable_notifications': settings.ENABLE_NOTIFICATIONS,
                                  'privileges': privileges,
                                  'user_repo_id': str(user_repo.ident)
                              },
                              RequestContext(request))

def login_page(request):
    """Login page for app
    """
    return render_to_response('ui/login.html', {},
                              RequestContext(request))

def logout_user(request):
    """log out of the Django session"""
    logout(request)
    return HttpResponseRedirect('/')

def privacy(request):
    """Privacy policy
    """
    return render_to_response('ui/privacy.html', {},
                              RequestContext(request))

def tos(request):
    """Terms of Service for app
    """
    return render_to_response('ui/tos.html', {},
                              RequestContext(request))