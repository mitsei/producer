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
        }
    });

    return SingleRun;
});