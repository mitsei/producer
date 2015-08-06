// app/dashboard/compositions/collections/compositions.js

define(["backbone",
    "apps/dashboard/compositions/models/composition"],
    function(Backbone, CompositionModel){

    var Compositions = Backbone.Collection.extend({
        model: CompositionModel
    });

    return Compositions;
});