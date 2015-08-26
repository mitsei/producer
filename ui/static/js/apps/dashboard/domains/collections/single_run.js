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
            var url = '/api/v1/repository/repositories/' + this.id,
                payload = {childIds: this.childIds};

            Backbone.ajax({
                url: url,
                data: JSON.stringify(payload),
                contentType: 'application/json',
                type: 'PUT',
                success: function () {
                    console.log('saved a run');
                }
            });
        }
    });

    return SingleRun;
});