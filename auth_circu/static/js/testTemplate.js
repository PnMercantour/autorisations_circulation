(function(){
  'use strict';

  var dzone = new Dropzone(".dropzone", {
    paramName: "file", // The name that will be used to transfer the file
    maxFilesize: 2, // MB
    createImageThumbnails: false,
    previewTemplate: document.querySelector("#template").parentNode.innerHTML,
    acceptedFiles: ".odt",
    dictDefaultMessage: "Glissez et déposez un modèle à tester ici"
  });

  // Hide the total progress bar when nothing's uploading anymore
  dzone.on("complete", function(result) {
    var bar = result.previewElement.querySelector('.progress-bar');
    if (result.status === "error"){
      bar.className = "progress-bar progress-bar-danger";
    } else {
      bar.className = "progress-bar progress-bar-success";
    }
  });

  angular.module('test_template', [
    'auth_circu',
    'ui.select',
  ]).controller('uploader', function() {

    var ctrl = this;
    ctrl.type = "other";

    dzone.on('sending', function(file, xhr, formData){
        formData.append('category', ctrl.type);
    });

 });

})();
