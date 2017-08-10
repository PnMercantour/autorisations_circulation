(function(){
'use strict';

angular.module('auth_circu', ['ui.bootstrap'])

.config(['$locationProvider', function($locationProvider) {
  // make sure we use HTML 5 APIs. E.G: browser history and no hash hack.
  // WARNING: this implies all the links that are not managed by angular
  // should be marked with target="_self". In this app we don't use angular
  // routing, hence all links must be marked with target="_self".
  $locationProvider.html5Mode(true);
}])

.service('storage', function(){
  var service = this;
  service.get = function(key, defaultValue){
    var res = localStorage.getItem(key);
    if (res === null){
      return defaultValue;
    }
    return JSON.parse(res);
  };
  service.set = function(key, value){
    localStorage.setItem(key, JSON.stringify(value));
  };
})

/**
 * Turn a collection into a listing of separated values
 */
.filter('join', function () {
    return function join(array, separator, prop) {
        if (!Array.isArray(array)) {
          throw('The join filter expects and array')
        }
        return (!!prop ? array.map(function (item) {
            return item[prop];
        }) : array).join(separator);
    };
})

/**
 *  Make all the strings follow the same format:
 *  "A     Cat   " => "a cat"
 *  "L'île-sur-noix !" => "l ile sur noix"
 */
.filter('normalize', function(){
    var specialMarks = /[\u0300-\u036f]/g;
    var spacing = /[ _\-']+/g;
    var nonAlphaNum = /[^a-z0-9 ]+/g;
    return function(str){

        str = str.normalize('NFD').replace(specialMarks, "")
        str = str.trim().toLowerCase().split(spacing).join(' ');
        return str.replace(nonAlphaNum, "");
    }
})

.directive('onEscape', function() {
    return {
        restrict: 'A',
        scope: {
          onEscape: "&"
        },
        link: function(scope, element, attrs, controller) {
            element.on('keydown', function(ev) {
              if (ev.keyCode != 27) return;
              scope.onEscape();
              scope.$apply();
            });
        },
    };
});


})();
