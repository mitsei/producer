// app/dashboard/compositions/models/composition.js

define(["backbone"],
    function(Backbone){

    var Composition = Backbone.Model.extend({
        initialize: function () {
            var children = this.get("children"),
                _this = this;
            if (children) {
                require(["apps/dashboard/compositions/collections/compositions"],
                    function (CompositionsCollection) {
                        _this.children = new CompositionsCollection(children);
                        _this.unset("children");
                });
            }
        },
        url: function () {
            return this.id ? '/api/v1/repository/compositions/' + this.id : '/api/v1/repository/compositions/';
        }
    });
    return Composition;
});