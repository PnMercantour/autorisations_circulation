var app = angular.module('autcircu', ['ui.bootstrap']);

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
