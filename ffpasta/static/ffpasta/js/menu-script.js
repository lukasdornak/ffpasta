
$(function(){
    $('#menu_button').click(function(event) {
        $('#menu_button').toggleClass('cross');
        $('nav').toggleClass('hidden');
    });
    $('nav a').click(function(event) {
        $('#menu_button').removeClass('cross');
        $('nav').addClass('hidden');
    });
});
