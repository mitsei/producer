// apps/curate/collections/banks.js

define(["backbone",
        "apps/curate/models/bank"],
    function(Backbone, BankModel){

    var Banks = Backbone.Collection.extend({
        initialize: function (models, options) {
        },
        model: BankModel,
        url: function () {
            return '/api/v1/learning/objectivebanks/?page=all';
        },
        parse: function (response) {
            return response.data.results;
        }
    });

    return Banks;
});