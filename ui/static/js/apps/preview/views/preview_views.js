// apps/preview/views/preview_views.js

define(["app",
        "apps/common/utilities",
        "apps/dashboard/assets/models/assets",
        "apps/dashboard/compositions/models/composition",
        "text!apps/preview/templates/resource_preview.html",
        "text!apps/preview/templates/composition_preview.html",
        "text!apps/preview/templates/unit_button.html",
        "text!apps/preview/templates/no_content.html",
        "bootstrap"],
       function(ProducerManager, Utils, AssetModel, CompositionModel,
                ResourceTemplate, CompositionTemplate, UnitButtonTemplate,
                NoContentTemplate){
  ProducerManager.module("PreviewApp.View", function(View, ProducerManager, Backbone, Marionette, $, _){
    function getAssets (childrenList) {
        return _.filter(childrenList, function (child) {
            return child.type !== 'Composition';
        });
    }

    function getCompositions (childrenList) {
        return _.filter(childrenList, function (child) {
            return child.type === 'Composition';
        });
    }

    function matchListOrder (originalList, secondList) {
        // sort a secondList according to the order in originalList
        // assumes the exact same items are in both lists, just in
        // different order
        var temporaryList = [];

        _.each(originalList, function (item) {
            temporaryList.push(_.filter(secondList, function (item2) {
                return item.id === item2.id;
            })[0]);
        });

        return temporaryList;
    }

    View.ResourceView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        template: false,
        onRender: function (e) {
            var serializedData = this.options,
                resource = new AssetModel({
                    id: serializedData.objId,
                    renderable: true
                }),
                promise = resource.fetch(),
                _this = this,
                resource,
                sourceDoc;

            Utils.processing();

            promise.done(function (data) {
                var video = false;
                Utils.doneProcessing();
                if (data.type === 'Asset') {
                    var assetText = data.assetContents[0].text.text;

                    if (assetText.indexOf('youtube') >= 0) {
                        var youtubeIds = $(assetText).attr('youtube')
                                .split(','),
                            youtubeId = _.filter(youtubeIds, function (speedIdPair) {
                                return speedIdPair.indexOf('1.0:') >= 0;
                            })[0].split(':')[1];

                        video = true;
                        sourceDoc = '//www.youtube.com/embed/' + youtubeId;
                    } else {
                        sourceDoc = Utils.wrapText(assetText);
                    }
                } else {
                    sourceDoc = Utils.wrapText(data.texts.edxml);
                }
                _this.$el.html(_.template(ResourceTemplate) ({
                    displayName: data.displayName.text,
                    resource: sourceDoc,
                    video: video
                }));
            });
        },
        events: {
        }
    });

    View.CompositionView = Marionette.ItemView.extend({
        initialize: function (options) {
            this.options = options;
            return this;
        },
        serializeData: function () {
            return {
                options: this.options
            };
        },
        tagName: 'div',
        className: 'composition-preview-wrapper',
        template: function () {
            return _.template(CompositionTemplate)();
        },
        onShow: function (e) {
            var serializedData = this.options,
                composition = new CompositionModel({
                    id: serializedData.objId,
                    renderable: true
                }),
                promise = composition.fetch({
                    reset: true,
                    error: function (model, xhr, options) {
                        ProducerManager.vent.trigger('msg:error', xhr.responseText);
                        Utils.doneProcessing();
                    }
                }),
                _this = this,
                $sidebarHeader = $('.sidebar-header'),
                $sidebarList = $('.sidebar-list'),
                sidebars;

            Utils.processing();

            promise.done(function (data) {
                Utils.doneProcessing();

                $sidebarHeader.text(data.displayName.text);
                sidebars = data.children;

                _this.updateButtons($sidebarList, sidebars, 'sidebar');
                _this.clearContents();
                _this.updateContents([], 'chapter');
            });
        },
        events: {
            'click .sidebar-btn': 'showChildrenCompositions',
            'click .vertical-btn': 'showAssets'
        },
        clearActiveSelf: function ($e) {
            $e.removeClass('active');
        },
        clearContents: function () {
            $('.content-list').empty();
        },
        clearVerticalBtns: function () {
            $('.vertical-list-wrapper').empty();
        },
        hideAssetsByClass: function (classToHide, classToRemove) {
            var $contentList = $('.content-list');

            $contentList.children('.' + classToHide + '-asset')
                .addClass('hidden');
            $contentList.children('.' + classToRemove + '-asset')
                .remove();
        },
        setActiveState: function ($e) {
            $e.siblings().removeClass('active');
            $e.addClass('active');
        },
        showAssets: function (e) {
            var $e = $(e.currentTarget),
                $obj = $e.data('obj'),
                contents = [],// at this level don't need to filter out...only assets
                numContents = contents.length,
                renderableContents = [],
                _this = this;

            if ($obj.hasOwnProperty('children')) {
                contents = $obj.children;
                numContents = contents.length;
            }

            if ($obj.hasOwnProperty('type')) {
                if ($obj.type === 'Asset' || $obj.type === 'Item') {
                    contents = [$obj];
                    numContents = contents.length;
                }
            }

            if (!$e.hasClass('active')) {
                _this.setActiveState($e);
                Utils.processing();
                _this.hideAssetsByClass('sidebar', 'vertical');

                if (contents.length > 0) {
                    _.each(contents, function (content) {
                        var resource = new AssetModel({
                                id: content.id,
                                renderable: true
                            }),
                            promise = resource.fetch();

                        promise.done(function (data) {
                            renderableContents.push(data);
                            if (--numContents === 0) {
                                renderableContents = matchListOrder(contents, renderableContents);

                                _this.updateContents(renderableContents, 'vertical');
                            }
                        });
                    });
                } else {
                    // put up a no content message
                    _this.updateContents([], 'vertical');
                }
            } else {
                _this.clearActiveSelf($e);
                _this.showAssetsByClass('sidebar', 'vertical');
            }
        },
        showAssetsByClass: function (classToShow, classToRemove) {
            var $contentList = $('.content-list');

            $contentList.children('.' + classToShow + '-asset')
                .removeClass('hidden');
            $contentList.children('.' + classToRemove + '-asset')
                .remove();
        },
        showChildrenCompositions: function (e) {
            var $e = $(e.currentTarget),
                $obj = $e.data('obj'),
                $verticalList = $('.vertical-list-wrapper'),
                renderableContents = [],
                _this = this,
                $children = [],
                contents = [],
                numContents = contents.length;

            if ($obj.hasOwnProperty('children')) {
                $children = $obj.children;
            }

            if ($obj.hasOwnProperty('type')) {
                if ($obj.type === 'Asset' || $obj.type === 'Item') {
                    contents = [$obj];
                    numContents = contents.length;
                }
            }

            if (!$e.hasClass('active')) {
                _this.setActiveState($e);

                _this.clearVerticalBtns();
                _this.updateButtons($verticalList, $children, 'vertical');
                _this.hideAssetsByClass('chapter', 'sidebar');
                _this.hideAssetsByClass('chapter', 'vertical');

                $verticalList.find('.vertical-btn')
                    .css('width', Math.floor(100 / $children.length) + '%');

                Utils.processing();

                if (contents.length > 0) {
                    _.each(contents, function (content) {
                        var resource = new AssetModel({
                                id: content.id,
                                renderable: true
                            }),
                            promise = resource.fetch();

                        promise.done(function (data) {
                            renderableContents.push(data);
                            if (--numContents === 0) {
                                // need to re-order renderableContents per
                                // the order in the original contents
                                renderableContents = matchListOrder(contents, renderableContents);

                                _this.updateContents(renderableContents, 'sidebar');
                            }
                        });
                    });
                } else {
                    // put up a No Content message
                    _this.updateContents([], 'sidebar');
                }
            } else {
                _this.clearActiveSelf($e);
                _this.showAssetsByClass('chapter', 'sidebar');
                _this.clearVerticalBtns();
                _this.clearContents();
                _this.updateContents([], 'sidebar');
            }
        },
        updateButtons: function ($list, $items, tag) {
            if ($items.length === 0) {
                $list.addClass('hidden');
            } else {
                $list.removeClass('hidden');
                this.clearVerticalBtns();
                _.each($items, function (item) {
                    $list.append(_.template(UnitButtonTemplate)({
                        buttonType: tag,
                        displayName: item.displayName.text,
                        rawObj: JSON.stringify(item)
                    }));
                })
            }
        },
        updateContents: function (contents, className) {
            var $contentList = $('.content-list'),
                $wrapper = $('<div></div>');
            Utils.doneProcessing();
            if (contents.length > 0) {
                _.each(contents, function (content) {
                    var video = false;
                    if (content.type === 'Asset') {
                        var assetText = content.assetContents[0].text.text;

                        if (assetText.indexOf('youtube=') >= 0) {
                            var youtubeIds = $(assetText).attr('youtube')
                                    .split(','),
                                youtubeId = _.filter(youtubeIds, function (speedIdPair) {
                                    return speedIdPair.indexOf('1.0:') >= 0 ||
                                        speedIdPair.indexOf('1.00:') >= 0;
                                })[0].split(':')[1];

                            video = true;
                            sourceDoc = '//www.youtube.com/embed/' + youtubeId;
                        } else {
                            sourceDoc = Utils.wrapText(assetText);
                        }
                    } else {
                        sourceDoc = Utils.wrapText(content.texts.edxml);
                    }
                    $wrapper.append(_.template(ResourceTemplate)({
                        displayName: content.displayName.text,
                        resource: sourceDoc,
                        video: video
                    }));
                    $wrapper.addClass(className + '-asset');
                    $contentList.append($wrapper);
                });

                $contentList.find('iframe').each(function () {
                    $(this).load(function () {
                        $(this).css('height', $(this).contents().height());
                    });
                });
            } else {
                $wrapper.append(_.template(NoContentTemplate)());
                $wrapper.addClass(className + '-asset');
                $contentList.append($wrapper);
            }
        }
    });

  });

  return ProducerManager.PreviewApp.View;
});