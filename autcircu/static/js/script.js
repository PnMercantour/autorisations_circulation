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
  $location
) {
  var vm = this;

  // trick to avoid an AJAX request on first load. This
  // data is inlined in the HTML page.
  // We also store it in local storage to
  // keep the last used value at the next reload
  var cache = storage.get('pagination', window.PRELOAD_PAGINATION);
  var queryString = $location.search();
  vm.pagination = angular.merge({}, cache, queryString);

  vm.authorizations = AuthListing;
  vm.loading = true;
  vm.error = '';

  vm.refreshPagination = function(){
    Object.entries(vm.pagination).forEach(function(params){
      $location.search(params[0], params[1]);
    });
    storage.set('pagination', vm.pagination);
    vm.loading = true;
    vm.error = "";
    vm.authorizations.load_authorizations(
      vm.pagination.year,
      vm.pagination.month,
      vm.pagination.status
    ).then(function(){
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

  vm.refreshPagination();

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
