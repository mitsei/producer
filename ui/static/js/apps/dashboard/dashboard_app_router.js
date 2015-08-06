// app/dashboard/dashboard_app_router.js

define(["app"],
    function(ProducerManager){
  ProducerManager.module("Routers.ProducerApp", function(ProducerAppRouter, ProducerManager, Backbone, Marionette, $, _){
    ProducerAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
        "repos/new": "addDomainRepo",
        "repos/:id": "showRepoCourses"
      }
    });

    var getMatchingDomainOption = function (path) {
        var domainRepoOptions = $('.repositories-menu li a'),
            domainMatch;

        domainMatch = _.filter(domainRepoOptions, function (opt) {
            return $(opt).attr('href') === path;
        })[0];

        return domainMatch;
    };

    var fixDomainSelector = function (expectedPath) {
        var domainMatch = getMatchingDomainOption(expectedPath),
            $repoBtn = $('.dropdown-toggle');

        $repoBtn.find('span.repository-placeholder').text($(domainMatch).text());
        $('.repository-menu').data('id', $(domainMatch).data('id'));
        $("ul.repository-navbar li").removeClass('hidden');
    };

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("ProducerApp");
      action(arg);
    };

    var selectedRepoId = function (path) {
        var domainMatch = getMatchingDomainOption('#repos/' + path);
        return $(domainMatch).data('id');
    };

    var API = {
      addDomainRepo: function(){
          fixDomainSelector('#repos/new');
      },

      showRepoCourses: function(id){
        fixDomainSelector('#repos/' + id);
        id = selectedRepoId(id);
        require(["apps/dashboard/domains/domain_controller"], function(DomainController){
          executeAction(DomainController.listCourses, id);
        });
      }

    };

    ProducerManager.on("repos:show", function(id){
      ProducerManager.navigate("repos/" + id);
      API.showRepoCourses(id);
    });

    ProducerManager.Routers.on("start", function(){
      new ProducerAppRouter.Router({
        controller: API
      });

      // bind the click events
      $(".repositories-menu li a").on('click', function () {
          fixDomainSelector($(this).attr('href'));
      });
    });
  });

  return ProducerManager.ProducerAppRouter;
});