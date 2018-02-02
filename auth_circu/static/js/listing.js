/*jshint esversion: 6 */

(function(){
'use strict';

angular.module('auth_circu')

.service('AuthListing', function($http, $filter){

  var service = this;
  var angularFilter = $filter('filter');
  var normalize = $filter('normalize');

  service.listing = [];
  service.filteredListing = [];

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
  };

  service.filterAuthorizations = function(filters){

    if (!filters.length){
      service.filteredListing = service.listing;
      return;
    }

    service.filteredListing =  angularFilter(

      service.listing,

      // this function is going to be called quite often, so we use regular
      // loops to avoid to many function calls
      function (authRequest, index, array) {

        // one of the filters must be ok
        for (var i = 0; i < filters.length; i++){

          var filter = filters[i];

          // check the request author name
          if (normalize(authRequest.author_name || '').indexOf(filter) !== -1){
            return true;
          }

          // check the auth number
          if (normalize(authRequest.number).indexOf(filter) !== -1){
            return true;
          }

          // check the places names and st
          for (var y = 0, l = authRequest.places.length; y < l; y++) {
            var name = normalize(authRequest.places[y].name);
            if (name.indexOf(filter) !== -1){
              return true;
            }
            var st = normalize(authRequest.places[y].st);
            if (st.indexOf(filter) !== -1){
              return true;
            }
          }

          // check the vehicule numberplate
          for (y = 0, l = authRequest.vehicules.length; y < l; y++) {
            var numberplate = normalize(authRequest.vehicules[y]);
            if (numberplate.indexOf(filter) !== -1){
              return true;
            }
          }
        }

        return false;
      }

    );
  };
})

.controller('AuthListingCtrl', function(
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
  // make it available globally to avoid the cost of injection in the
  // <places> component
  window.__join_filter = $filter('join');

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
  };

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
        vm.error = "Impossible de charger la liste des autorisations. Vérifiez votre connexion, puis rechargez cette page.";
      } else {
        vm.error = "Erreur en chargant la liste des autorisations. Rechargez la page. Si ce message ne disparait pas, contactez un administrateur.";
        console.error('Error loading the auth listing:', error.data);
      }
    });
  };

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
  };


  // We use $timeout here to space digests and ensure we see the loading
  // wheel

  // triggered when we submit the search form with  click or "enter"
  // to filter the listing
  vm.onSubmitSearch = function(e){
    e.preventDefault();
    vm.loading = true;
    $timeout(function(){
      vm.refreshSearchFilter();
      vm.loading = false;
    });
  };

  // triggered when we clear the search input by clicking on the cross button
  // or typing "escape"
  vm.onClearSearch = function(){
    vm.loading = true;
    $timeout(function(){
      vm.search = '';
      vm.refreshSearchFilter();
      vm.loading = false;
    });
  };

  // triggered every time we change the searched team. Update the listing
  // when empty
  vm.onChange = function(){
    if (!vm.search){
      vm.loading = true;
      $timeout(function(){
        vm.refreshSearchFilter();
        vm.loading = false;
      });
    }
  };

  vm.onDownloadODS = function(){

    // Display a modal windows with a spinner while the document is
    // being generated. We also want that if the document takes too long
    // to be created, the user can cancel the request by clicking on the
    // cancel button.
    var canceler = $q.defer();
    var scope = {};

    // show modal with spinner
    var modalWindow = $uibModal.open({
      templateUrl: 'loading-modal.html',
      controllerAs: 'vm',
      controller: function ($uibModalInstance) {
        this.scope = scope;
        this.scope.status = 'loading';
        this.scope.error = '';
        this.cancel = function () {
          // dismiss the windows if the cancel button is clicked
          canceler.resolve();
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
        modalWindow.close();
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

  };

  vm.onDownloadPDF = function(){

    // Same workflows as for onDownloadODS
    var canceler = $q.defer();
    var scope = {};
    var modalWindow = $uibModal.open({
      templateUrl: 'loading-modal.html',
      controllerAs: 'vm',
      controller: function ($uibModalInstance) {
        this.scope = scope;
        this.scope.status = 'loading';
        this.scope.error = '';
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
        modalWindow.close();
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
  };

  vm.onDownloadAuthDocs = function(e, auth){
    e.preventDefault();
    // Same workflows as for onDownloadODS
    var canceler = $q.defer();
    var scope = {};
    var modalWindow = $uibModal.open({
      templateUrl: 'loading-modal.html',
      controllerAs: 'vm',
      controller: function ($uibModalInstance) {
        this.scope = scope;
        this.scope.status = 'loading';
        this.scope.error = '';
        this.cancel = function () {
          // dismiss the windows if the cancel button is clicked
          $uibModalInstance.dismiss('cancel');
        };
      }
    });

    // if cancel button has been clicked, we abort the request
    modalWindow.result.then(function(){}, canceler.resolve);

    return $http.post(
        "/exports/authorizations/" + auth.id,
        {},
        {responseType: 'arraybuffer', timeout: canceler.promise}
    ).then(function(response) {
        modalWindow.close();
        var blob = new Blob(
            [response.data],
            {type: "application/vnd.oasis.opendocument.text;charset=charset=utf-8"}
        );
        var date = $filter('date')(new Date(), "yyyy-MM-dd");
        saveAs(blob, `${auth.author_name}_${date}.odt`);
    }, function(error){
      scope.status = "error";
      if (error.status === -1){ // ignore error from the user aborting the request
        return;
      }
      if (error.status === 500){ // server error
        console.log(error)
        scope.error = "Erreur inconnue. Veuillez réessayer ou contactez un administrateur.";
        return;
      }
      var str = String.fromCharCode.apply(null, new Uint8Array(error.data));
      scope.error = JSON.parse(str).message;
    }).finally();
  };

  // populate de listing
  vm.refreshDateFilter();
});


})();
