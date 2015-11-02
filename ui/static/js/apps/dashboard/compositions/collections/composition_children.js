// app/dashboard/compositions/collections/composition_children.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var Compositions = Backbone.Collection.extend({
        initialize: function (models, options) {
            this.id = options.id;
            this.repoId = options.repoId;
        },
        model: CompositionModel,
        url: function () {
            return '/api/v1/repository/repositories/' + this.repoId + '/compositions/' + this.id + '/children/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return Compositions;
});