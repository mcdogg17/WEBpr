var sc_width = document.documentElement.clientWidth
var sc_height = document.documentElement.clientHeight
var path = document.location.pathname
var size = '19'
var board_size = Math.min(sc_width, sc_height) - 200
var node_size = board_size / (String(+size + +'1'))

socket = io.connect('http://' + document.domain + ':' + location.port + '/');

var prev_color = 'black'


socket.on('moved', function(data) {
    // Обновляем картинку игровой доски
    document.getElementById('status').innerHTML = 'Ходит: ' + data.name
    prev_color = data.color
    d = new Date()
    $('#board-pic').attr("src", "/static/img/" + data.game_id + ".png?" + d.getTime())
    var picture = document.getElementById('board-pic')
    var padding = node_size / 2
    picture.style.paddingRight = padding
    picture.style.width = String(board_size) + 'px'
    picture.style.height = String(board_size) + 'px'

    black = document.getElementById('black-score')
    black.innerHTML = black.innerHTML.split(':')[0] + ': ' +  data.score.black

    white = document.getElementById('white-score')
    white.innerHTML = white.innerHTML.split(':')[0] + ': ' + data.score.white

});

socket.on('end', function(data) {
    res = document.getElementById('status')
    if (data.winner) {
    res.innerHTML = 'Победил ' + data.winner + '!'
    } else {
    res.innerHTML = 'Ничья!'
    }
});

socket.on('pass', function(data) {

});

function leave_game() {
    socket.emit("leave_game");
}

function make_move(move) {
    socket.emit('make_move', {'move': move, 'prev_color': prev_color});
}

function pass() {
    socket.emit('make_move', {'move': '', 'prev_color': prev_color});
}


window.onload = window.onresize = function set_size() {
    // После загрузки страницы подстраиваем размеры
    sc_width = document.documentElement.clientWidth
    sc_height = document.documentElement.clientHeight
    board_size = Math.min(sc_width, sc_height) - 200
    node_size = board_size / (String(+size + +'1'))

    var board_container = document.getElementById('board-container')
    var picture = document.getElementById('board-pic')
    var table = document.getElementById('table')

    // Задаем размеры игровой доски
    board_container.style.width = String(board_size) + 'px'
    board_container.style.height = String(board_size) + 'px'

    // Задаем размеры для чата
    var chat = document.getElementById('chat')
    var txt_field = document.getElementById('msg_text')
    var send_btn = document.getElementById('send_msg')
    chat.cols = sc_width / 25
    chat.rows = board_size / 35
    txt_field.size = Math.max(chat.cols - 18, 1)


    // Задаем размеры и отступ картинки доски
    var padding = node_size / 2
    picture.style.paddingRight = padding
    picture.style.width = String(board_size) + 'px'
    picture.style.height = String(board_size) + 'px'

    table.style.marginLeft = String(node_size / 2) + 'px'
    table.style.marginTop = String(node_size / 2) + 'px'

    // Устанавливаем размеры для клеток таблицы игровой доски
    for (var row=0; row < size; row++){
        for (var col=0; col < size; col++){
            var id = 'td_{row}_{col}'.replace('{row}', row).replace('{col}', col)
            document.getElementById(id).style.width = String(node_size) + 'px'
            document.getElementById(id).style.height = String(node_size) + 'px'
        }
    }
}