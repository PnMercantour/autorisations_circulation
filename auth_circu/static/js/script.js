(function(){
'use strict';

var app = angular.module('auth_circu', ['ui.bootstrap']);

app.config(['$locationProvider', function($locationProvider) {
  // make sure we use HTML 5 APIs. E.G: browser history and no hash hack.
  // WARNING: this implies all the links that are not managed by angular
  // should be marked with target="_self". In this app we don't use angular
  // routing, hence all links must be marked with target="_self".
  $locationProvider.html5Mode(true);
}]);

app.controller('LoginFormCtrl', function($http, $location){
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
      console.log('location', $location.search(), $location.search().next, location.search);
      window.location = $location.search().next || "/authorizations";
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

app.service('AuthListing', function($http, $filter){

  var service = this;
  var angularFilter = $filter('filter');
  var normalize = $filter('normalize');

  service.listing = [];
  service.filteredListing = []

  service.loadAuthorizations = function(year, month, status){
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

  service.filterAuthorizations = function(filters){

    if (!filters.length){
      service.filteredListing = service.listing;
      return
    }

    service.filteredListing =  angularFilter(

      service.listing,

      // this function is going to be called quite often, so we use regular
      // loops to avoid to many function calls
      function (authRequest, index, array) {

        var ok = false;

        // all filters must be ok
        mainLoop: for (var i = 0; i < filters.length; i++){

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
  AuthListing,
  storage,
  $location,
  $filter,
  $scope,
  $timeout,
  $http,
  $uibModal,
  $q
) {
  var vm = this;
  var normalize = $filter('normalize');

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
    return vm.authorizations.loadAuthorizations(
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

    var filters = vm.search.trim();

    if (filters) {
      filters = filters.split(/[\s+\+?\s+]+/).map(function(filter){
          return normalize(filter);
      });
    } else {
      filters = [];
    }

    vm.authorizations.filterAuthorizations(filters);
  }


  // We use $timeout here to space digests and ensure we see the loading
  // wheel

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

  // triggered every time we change the searched team. Update the listing
  // when empty
  vm.onChange = function(){
    if (!vm.search){
      vm.loading = true
      $timeout(function(){
        vm.refreshSearchFilter();
        vm.loading = false;
      })
    }
  }

  vm.onDownloadODS = function(){

    // Display a modal windows with a spinner while the document is
    // being generated. We also want that if the document takes too long
    // to be created, the user can cancel the request by clicking on the
    // cancel button.
    var canceler = $q.defer();

    // show modal with spinner
    var modalWindow = $uibModal.open({
      templateUrl: 'loading-modal.html',
      controllerAs: 'vm',
      controller: function ($uibModalInstance) {
        this.cancel = function () {
          // dismiss the windows if the cancel button is clicked
          canceler.resolve()
          $uibModalInstance.dismiss('cancel');
        };
      }
    });

    // if cancel button has been clicked, we abort the request
    modalWindow.result.then(function(){}, canceler.resolve);

    // make the AJAX request to get the document
    return $http.post(
        "/exports/authorizations?format=ods",
        {authorizations: vm.authorizations.filteredListing},
        {responseType: 'arraybuffer', timeout: canceler.promise}
    ).then(function(response) {
        // document is generated, close the modal and prompt for download
        modalWindow.close()
        var blob = new Blob(
            [response.data],
            {type: "application/vnd.oasis.opendocument.spreadsheet;charset=charset=utf-8"}
        );
        var date = $filter('date')(new Date(), "yyyy-MM-dd_hh'h'mm'm'ss's'");
        saveAs(blob, `authorizations.${date}.ods`);

    }, function(error){
      if (error.status !== -1){ // ignore error from the user aborting the request
        console.error("Error while exporting to ODS", error);
      }
    });

  }

  vm.onDownloadPDF = function(){

    // Same workflows as for onDownloadODS
    var canceler = $q.defer();

    var modalWindow = $uibModal.open({
      templateUrl: 'loading-modal.html',
      controllerAs: 'vm',
      controller: function ($uibModalInstance) {
        this.cancel = function () {
          // dismiss the windows if the cancel button is clicked
          $uibModalInstance.dismiss('cancel');
        };
      }
    });

    // if cancel button has been clicked, we abort the request
    modalWindow.result.then(function(){}, canceler.resolve);

    return $http.post(
        "/exports/authorizations?format=pdf",
        {authorizations: vm.authorizations.filteredListing},
        {responseType: 'arraybuffer', timeout: canceler.promise}
    ).then(function(response) {
        modalWindow.close()
        var blob = new Blob(
            [response.data],
            {type: "application/pdf"}
        );
        var date = $filter('date')(new Date(), "yyyy-MM-dd_hh'h'mm'm'ss's'");
        saveAs(blob, `authorizations.${date}.pdf`);
    }, function(error){
      if (error.status !== -1){ // ignore error from the user aborting the request
        console.error("Error while exporting to PDF", error);
      }
    }).finally();
  }

  // populate de listing
  vm.refreshDateFilter();
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

})();
