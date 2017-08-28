(function(){
'use strict';

angular.module('auth_request', [
  'auth_circu',
  'ui.select',
  'ngSanitize'
])

.controller('RequestFormCtrl', function ($location, $http) {

  var vm = this;

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
    endDate: null,
    groupVehiculesOnDoc: false,
    category: $location.search().category || 'other',
    valid: false,
    rules: undefined
  }

  // we do this only when editing an existing request
  if (window.PRELOAD_REQUEST){
    vm.request = window.PRELOAD_REQUEST;
    vm.request.motive = vm.request.motive && vm.request.motive.id;

    var parseDate = function (string){
      if (!string){
        return null
      }

      string = string.split('/');
      return new Date(string[2], string[1], string[0]);
    }

    vm.request.requestDate = parseDate(vm.request.requestDate);
    vm.request.authStartDate = parseDate(vm.request.authStartDate);
    vm.request.authEndDate = parseDate(vm.request.authEndDate);
  }

  // salese is a specific case: it has date boundaries and a mandatory
  // place
  if (vm.request.category == "salese"){
    var piste = vm.places.filter(function(place){
      return place.name == "Piste de Salèse"
    })[0];

    // add saleze as a default place if the request is a new one
    if (!vm.request.id){
      vm.request.places.push(piste);
    }

    var year = (new Date()).getFullYear();
    // limit to 01/05 to 30/11
    vm.minRequestDate = new Date(year, 4, 1);
    vm.maxRequestDate = new Date(year, 10, 30);
  }

  vm.addDoc = function(e){
    e.preventDefault();
    vm.request.proofDocuments.push({
      type: "proofOfAddress",
      date: new Date(),
    });
    vm.requestForm.$setDirty();
  }

  vm.removeDoc = function(e, index){
    e.preventDefault();
    vm.request.proofDocuments.splice(index, 1);
    vm.requestForm.$setDirty();
  }

  vm.removePlace = function(e, index){
    e.preventDefault();
    if (vm.request.category === "salese" &&
        vm.request.places[index].name === "Piste de Salèse"){
        return
    }
    vm.request.places.splice(index, 1);
    if (!vm.request.length){
      vm.requestForm.places.$setValidity('required', true);
    }
    vm.requestForm.$setDirty();
  }

  vm.addPlace = function(newPlace){
    var isDuplicate = vm.request.places.some(function(place){
      return newPlace.id == place.id;
    });
    if (!isDuplicate){
      vm.request.places.push(newPlace);
      vm.newPlace = undefined;
      vm.requestForm.places.$setValidity('required', true);
    }
  }

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
      document.forms['vm.requestForm'].querySelector('.ng-invalid').focus()
      return
    }
    var request = angular.extend({}, vm.request, {valid: true});
    vm.saveDraft(e, request, 'saving').then(function(){
      vm.request.valid = true;
    })
  };

});

})();
