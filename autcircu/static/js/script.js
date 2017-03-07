var app = angular.module('autcircu', ['ui.bootstrap']);

app.controller('LoginFormCtrl', function($http){
  var vm = this;
  vm.loginData = {};
  vm.error = '';
  vm.login = function($event){
    $event.preventDefault();
    console.log(vm.loginData);

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
        console.log("Error while loging in. The server responded:");
        console.log(error);
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
