(function(){
'use strict';

angular.module('auth_circu')

.controller('LoginFormCtrl', function($http, $location){
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


})();
