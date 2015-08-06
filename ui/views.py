from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseRedirect, Http404

from dlkit.mongo.records.types import REPOSITORY_GENUS_TYPES

from dlkit_django.primitives import Type

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
    domain_repo_genus = Type(**REPOSITORY_GENUS_TYPES['domain-repo'])
    activate_managers(request)
    rm = get_session_data(request, 'rm')
    querier = rm.get_repository_query()
    querier.match_genus_type(domain_repo_genus, True)
    repos = rm.get_repositories_by_query(querier)
    return render_to_response('ui/dashboard.html',
                              {
                                  'repos': repos
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