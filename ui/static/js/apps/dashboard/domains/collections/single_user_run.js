// app/dashboard/domains/collections/single_user_run.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var SingleUserRun = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;  // run ID
        },
        model: CompositionModel,
        url: function () {
            return '/api/v1/repository/compositions/' + this.id;
        },
        parse: function (response) {
            return response.data.results;
        },
        save: function (options) {
            // hack the URL...which means you won't be able to fetch this again...
            var url = '/api/v1/repository/compositions/' + this.id,
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

    return SingleUserRun;
});