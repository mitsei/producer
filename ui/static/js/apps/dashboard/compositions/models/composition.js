// app/dashboard/compositions/models/composition.js

define(["backbone"],
    function(Backbone){

    var Composition = Backbone.Model.extend({
        initialize: function (options) {
            var children = this.get("children"),
                _this = this;
            if (children) {
                require(["apps/dashboard/compositions/collections/compositions"],
                    function (CompositionsCollection) {
                        _this.children = new CompositionsCollection(children);
                        _this.unset("children");
                });
            }
            this.options = options;
            return this;
        },
        url: function () {
            var url = this.id ? '/api/v1/repository/compositions/' + this.id : '/api/v1/repository/compositions/';

            if (this.options.renderable) {
                return url + '?fullMap';
            } else {
                return url;
            }
        },
        updateAssets: function (assetIds) {
            // update the composition's assetIds via PUT to <compositionId>/assets/
            if (this.id) {
                var url = '/api/v1/repository/compositions/' + this.id + '/assets/';

            }
        }
    });
    return Composition;
});