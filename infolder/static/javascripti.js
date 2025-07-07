
$(document).ready(function () {
    // Check if user saw the modal
    var key = 'hadModal',
        hadModal = localStorage.getItem(key);

    // Show the modal only if new user
    if (!hadModal) {
        $('#myModal').modal('show');
    }

    // If modal is displayed, store that in localStorage
    $('#myModal').on('shown.bs.modal', function () {
        localStorage.setItem(key, true);
    })
});

