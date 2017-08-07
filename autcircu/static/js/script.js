var app = angular.module('autcircu', ['ui.bootstrap']);


app.controller('LoginFormCtrl', function($http){
  var vm = this;
  vm.loginData = {};
  vm.error = '';
  vm.login = function($event){
    $event.preventDefault();

    $http({
      method: 'POST',
      url: '/auth/login',
      data: vm.loginData
    })
    .then(function(data) {
      window.location = "/authorizations";
    })
    .catch(function(error){

      if (error.status === 500) {
        vm.error = 'Le service connait actuellement un disfonctionnement. '+
                     ' Veuillez contacter un administrateur.';
        console.error("Error while loging in. The server responded:", error);
      } else {
        if (error.data.type == "login") {
          vm.error = "Nom d'utilisateur inconnu."
        }
        if (error.data.type == "password") {
          vm.error = "Mot de passe incorrect."
        }

      }
    })
  }
});

app.service('AuthListing', function($http){
  var service = this;
  service.listing = [];
  service.load_authorizations = function(year, month, status){
    return $http.get(
      "/api/v1/authorizations",
      {
        params: {
          year: year,
          month: month,
          status: status
        }
      }
    ).then(function(response) {
        service.listing = response.data;
    });
  }
})


app.service('storage', function(){
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
});


app.controller('AuthListingCtrl', function(
  $interval,
  AuthListing,
  storage,
  $location,
  $filter,
  $scope,
  $timeout
) {
  var vm = this;

  // Get the pagination values from several sources: the URL parameters,
  // the localStorage or the preloaded values from the server.
  var cache = storage.get('pagination', window.PRELOAD_PAGINATION);
  var queryString = $location.search();
  // search is an array so we deserialize it
  queryString.search = queryString.search ? JSON.parse(queryString.search) : [];
  vm.pagination = angular.merge({}, cache, queryString);

  vm.authorizations = AuthListing;
  vm.loading = true;
  vm.error = '';
  vm.search = '';
  vm.filteredListing = []

  vm.savePagination = function(){
    // Update the pagination values in the URL and local storage so that
    // we get them back if we come back later
    for (var [name, value] of Object.keys(vm.pagination)){
      // search is an array so we serialize it
      if (name === "search"){
        value = JSON.stringify(value);
      }
      $location.search(name, value);
    }
    storage.set('pagination', vm.pagination);
  }

  vm.refreshDateFilter = function(){

    vm.savePagination();

    // Update the listing with new data from the server with an Ajax call.;
    vm.loading = true;
    vm.error = "";
    return vm.authorizations.load_authorizations(
      vm.pagination.year,
      vm.pagination.month,
      vm.pagination.status
    ).then(function(){
      vm.refreshSearchFilter();
      vm.loading = false;
    }, function(error){
      if (error.status === -1){
        vm.error = "Impossible de charger la liste des autorisations. Vérifiez que votre connexion, puis rechargez cette page."
      } else {
        vm.error = "Erreur en chargant la liste des autorisations. Rechargez la page. Si ce message ne disparait pas, contactez un administrateur.";
        console.error('Error loading the auth listing:', error.data)
      }
    });
  }

  vm.refreshSearchFilter = function(){

    var normalize = $filter('normalize');

    var filters = vm.search.trim();
    // shortcut when there is no need to filter
    if (!filters){
      vm.filteredListing = vm.authorizations.listing;
      return
    }

    filters = filters.split(/[\s+\+?\s+]+/).map(function(filter){
        return normalize(filter);
    });

    var filterSize = filters.length;

    vm.filteredListing =  $filter('filter')(

      vm.authorizations.listing,

      function(authRequest, index, array) {

        var ok = false;

        // all filters must be ok
        mainLoop: for (var i = 0; i < filterSize; i++){

          var filter = filters[i];


          // check the request author name
          if (normalize(authRequest.author_name || '').indexOf(filter) !== -1){
            continue mainLoop;
          }

          // check the places names
          for (var y = 0; y < authRequest.places.length; y++) {
            var place = normalize(authRequest.places[y].name);
            if (place.indexOf(filter) !== -1){
              continue mainLoop;
            }
          }

          // check the vehicule numberplate
          for (var y = 0; y < authRequest.vehicules.length; y++) {
            var numberplate = normalize(authRequest.vehicules[y]);
            if (numberplate.indexOf(filter) !== -1){
              continue mainLoop;
            }
          }

          return false;

        }
        return true;
      }

    );


  }

  vm.refreshDateFilter();

  // triggered when we submit the search form with  click or "enter"
  // to filter the listing
  vm.onSubmitSearch = function(e){
    e.preventDefault();
    vm.loading = true
    $timeout(function(){
      vm.refreshSearchFilter();
      vm.loading = false;
    })
  }

  // triggered when we clear the search input by clicking on the cross button
  // or typing "escape"
  vm.onClearSearch = function(){
    vm.loading = true
    $timeout(function(){
      vm.search = '';
      vm.refreshSearchFilter();
      vm.loading = false;
    })
  }
})

app.controller('RequestFormCtrl', function () {

  /* For Salèse, limit to 01/05 to 30/11 */

  this.requestData = {
    requestDate: new Date()
  }

  // $scope.dateOptions = {
  //   maxDate: new Date(2020, 5, 22),
  //   startingDay: 1
  // };


});


/**
 * Turn a collection into a listing of separated values
 */
app.filter('join', function () {
    return function join(array, separator, prop) {
        if (!Array.isArray(array)) {
          throw('The join filter expects and array')
        }
        return (!!prop ? array.map(function (item) {
            return item[prop];
        }) : array).join(separator);
    };
});

/**
 *  Make all the strings follow the same format:
 *  "A     Cat   " => "a cat"
 *  "L'île-sur-noix !" => "l ile sur noix"
 */
app.filter('normalize', function(){
    var specialMarks = /[\u0300-\u036f]/g;
    var spacing = /[ _\-']+/g;
    var nonAlphaNum = /[^a-z0-9 ]+/g;
    return function(str){

        str = str.normalize('NFD').replace(specialMarks, "")
        str = str.trim().toLowerCase().split(spacing).join(' ');
        return str.replace(nonAlphaNum, "");
    }
})

app.directive('onEscape', function() {
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
