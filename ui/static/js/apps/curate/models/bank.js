// app/curate/models/bank.js

define(["backbone"],
    function(Backbone){

    var Bank = Backbone.Model.extend({
        url: function () {
            return this.id ? '/api/v1/learning/objectivebanks/' + this.id : '/api/v1/learning/objectivebanks/';
        }
    });
    return Bank;
});