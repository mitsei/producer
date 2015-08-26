// app/dashboard/domains/collections/single_run.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var SingleRun = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;  // run ID
        },
        model: CompositionModel,
        url: function () {
            return '/api/v1/repository/repositories/' + this.id + '/compositions/?nested&page=all';
        },
        parse: function (response) {
            return response.data.results;
        },
        save: function (options) {
            // hack the URL...which means you won't be able to fetch this again...
            this.url = '/api/v1/repository/repositories/' + this.id;
            this.sync('update', this, options);
        }
    });

    return SingleRun;
});