// app/dashboard/compositions/collections/composition_children.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var Compositions = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
        },
        model: CompositionModel,
        url: function () {
            return '/api/v1/repository/compositions/' + this.id + '/children/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return Compositions;
});