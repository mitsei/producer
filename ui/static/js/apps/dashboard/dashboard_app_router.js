// app/dashboard/dashboard_app_router.js

define(["app",
        "apps/common/utilities"],
    function(ProducerManager, Utils){
  ProducerManager.module("Routers.ProducerApp", function(ProducerAppRouter, ProducerManager, Backbone, Marionette, $, _){
    ProducerAppRouter.Router = Marionette.AppRouter.extend({
      appRoutes: {
        "repos/new": "addDomainRepo",
        "repos/:id": "showRepoCourses"
      }
    });

    var executeAction = function(action, arg){
      ProducerManager.startSubApp("ProducerApp");
      action(arg);
    };

    var API = {
      addDomainRepo: function(){
          Utils.fixDomainSelector('#repos/new');
      },

      showRepoCourses: function(id){
        Utils.fixDomainSelector('#repos/' + id);
        id = Utils.selectedRepoId(id);
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

      // bind the click events. This should go into a Navbar view somewhere...
      $(".repositories-menu li a").on('click', function () {
          Utils.fixDomainSelector($(this).attr('href'));
      });


//      $("#add-new-components-btn").sidr({
//          source: '#search-components-menu',
//          side: 'right',
//          name: 'component-search-sidr'
//      });
    });
  });

  return ProducerManager.ProducerAppRouter;
});