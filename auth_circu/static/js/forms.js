(function(){
'use strict';

angular.module('auth_request', [
  'auth_circu',
  'ui.select',
  'ngSanitize',
])

// This controller is starting to get big and include many conditional.
// It may be a good thing to delegate some of it's behavior to a 3 services,
// one for each letter type.
.controller('RequestFormCtrl', function ($location, $http, $filter, $q, $uibModal) {

  var vm = this;

  var normalize = $filter('normalize');

  vm.places = window.PRELOAD_PLACES;
  vm.minRequestDate = undefined;
  vm.maxRequestDate = undefined;
  vm.status = "start";

  vm.request = {
    requestDate: new Date(),
    motive: null,
    proofDocuments: [],
    authorName: null,
    authorGender: null,
    authorAddress: null,
    authorPhone: null,
    rules: null,
    places: [],
    vehicules: [],
    authStartDate: null,
    authEndDate: null,
    endDate: null,
    groupVehiculesOnDoc: false,
    category: $location.search().category || 'other',
    valid: false,
  };

  // we do this only when editing an existing request
  if (window.PRELOAD_REQUEST){
    vm.request = window.PRELOAD_REQUEST;
    vm.request.motive = vm.request.motive && vm.request.motive.id;

    var parseDate = function (string){
      if (!string){
        return null;
      }

      string = string.split('/');
      return new Date(string[2], string[1], string[0]);
    };

    vm.request.requestDate = parseDate(vm.request.requestDate);
    vm.request.authStartDate = parseDate(vm.request.authStartDate);
    vm.request.authEndDate = parseDate(vm.request.authEndDate);
    vm.request.proofDocuments = vm.request.proofDocuments.map(function(doc){
        doc.date = new Date(doc.date);
        return doc;
    });
  }

  // salese is a specific case: it has date boundaries and a mandatory
  // place
  if (vm.request.category == "salese"){
    var piste = vm.places.filter(function(place){
      return normalize(place.name).indexOf("salese") != -1;
    })[0];

    // add saleze as a default place if the request is a new one
    if (!vm.request.id){
      vm.request.places.push(piste);
    }

    var year = (new Date()).getFullYear();
    // limit to 01/05 to 30/11
    vm.minRequestDate = new Date(year, 4, 1);
    vm.maxRequestDate = new Date(year, 10, 30);

    // default dates have the limits for initial values
    vm.request.authStartDate = vm.request.authStartDate || vm.minRequestDate;
    vm.request.authEndDate = vm.request.authEndDate || vm.maxRequestDate;
  }

  vm.addDoc = function(e){
    e.preventDefault();
    vm.request.proofDocuments.push({
      type: "proofOfAddress",
      date: new Date(),
    });
    vm.requestForm.$setDirty();
  };

  vm.removeDoc = function(e, index){
    e.preventDefault();
    vm.request.proofDocuments.splice(index, 1);
    vm.requestForm.$setDirty();
  };

  vm.removePlace = function(e, index){
    e.preventDefault();
    if (vm.request.category === "salese" &&
       normalize(vm.request.places[index].name).indexOf("salese") != -1){
        return;
    }
    vm.request.places.splice(index, 1);
    if (!vm.request.length){
      vm.requestForm.places.$setValidity('required', true);
    }
    vm.requestForm.$setDirty();
  };

  vm.addPlace = function(newPlace){
    var isDuplicate = vm.request.places.some(function(place){
      return newPlace.id == place.id;
    });
    if (!isDuplicate){
      vm.request.places.push(newPlace);
      vm.newPlace = undefined;
      vm.requestForm.places.$setValidity('required', true);
    }
  };

  vm.deleteDraft = function(e) {
    e.preventDefault();
    if (confirm('Voulez-vous vraiment supprimer ce brouillon ?')){
      $http.delete('/api/v1/authorizations/' + vm.request.id);
      window.location = '/authorizations';
    }
  };

  vm.saveDraft = function(e, request, savingStatus) {
    e.preventDefault();
    vm.status = savingStatus || 'savingDraft';
    request = request || vm.request;
    vm.requestForm.$setSubmitted();

    if (!request.id){
      return $http.post('/api/v1/authorizations', request)
                  .then(function(response){
        vm.requestForm.$setPristine();
        window.location = '/authorizations/' + response.data.id + "#footer";
      });
    } else {
      return $http.put('/api/v1/authorizations/' + request.id, request)
           .then(function(){
        vm.requestForm.$setPristine();
        vm.status = 'start';
      });
    }

  };

  vm.save = function(e) {
    e.preventDefault();
    vm.requestForm.$setSubmitted();
    if (!vm.request.places.length){
      vm.requestForm.places.$setValidity('required', false);
    }
    // force all fields to a dirty state
    if (vm.requestForm.$invalid) {
      angular.forEach(vm.requestForm.$error, function(controls, errorName) {
          angular.forEach(controls, function(control) {
              control.$setDirty();
          });
      });
      document.forms['vm.requestForm'].querySelector('.ng-invalid').focus();
      return;
    }
    var request = angular.extend({}, vm.request, {valid: true});
    vm.saveDraft(e, request, 'saving').then(function(){
      vm.request.valid = true;
    });
  };

  // this is a duplicate of the code in listing.js. We may want to refactor
  // that
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

});

})();
