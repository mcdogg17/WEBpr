socket = io.connect('http://' + document.domain + ':' + location.port + '/');


socket.on('update_lobbies_list', (data) => {
    $('#lobbies_list').html('');
    var lobbies = data.lobbies
    for (var i=0; i < lobbies.length; i++) {
        $('#lobbies_list').append('<a id=' + lobbies[i][1] + ' ' + 'class="list-group-item list-group-item-action"' + ' >'+ lobbies[i][0] + ' </a>');
    }
});
