from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth.decorators import login_required, user_passes_test

from django.contrib.auth import authenticate, login, logout

from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404

from .utilities import *

def unexpired_user(user):
    return user.is_still_active_staff()

def check_credentials(request):
    username = request.POST['username']
    password = request.POST['password']
    redirect_url = request.POST['next']

    try:
        user = authenticate(username = username, password = password)
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
        log_error('mecqbank_ui.views.check_credentials()', ex)
        return HttpResponseForbidden("Bad credentials provided.")
    except Exception as ex:
        msg = log_error('mecqbank_ui.views.check_credentials()', ex)
        return Http404(msg)

@login_required()
@user_passes_test(unexpired_user)
def dashboard(request):
    """Dashboard for app
    """
    return render_to_response('mecqbank_ui/dashboard.html', {},
                              RequestContext(request))

def login_page(request):
    """Login page for app
    """

    return render_to_response('mecqbank_ui/login.html', {},
                              RequestContext(request))

def privacy(request):
    """Privacy policy
    """
    return render_to_response('mecqbank_ui/privacy.html', {},
                              RequestContext(request))

def tos(request):
    """Terms of Service for app
    """
    return render_to_response('mecqbank_ui/tos.html', {},
                              RequestContext(request))