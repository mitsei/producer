// app/dashboard/domains/models/repository.js

define(["backbone"],
    function(Backbone){

    var Repository = Backbone.Model.extend({
        url: function () {
            return this.id ? '/api/v1/repository/repositories/' + this.id : '/api/v1/repository/repositories/';
        }
    });
    return Repository;
});