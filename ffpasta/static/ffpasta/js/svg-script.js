
function get_headline_points($headline_group, $svg) {
    var svg_offset = $svg.parent().offset().top;
    var $headlines = $headline_group.children();
    var points = [];
    var top = $headlines.eq(0).offset().top + (parseInt($headlines.eq(0).css('height').replace('px', '')) / 2 ) - svg_offset;
    for (var i = 0; i < $headlines.length -1 ; i++) {
        points[i] = "M " + ($headlines.eq(i).offset().left + parseInt($headlines.eq(i).css('width').replace('px', ''))) + " " + top +
            " L " + $headlines.eq(i + 1).offset().left + " " + top;
    }
    return points;
}

function connect_headline_groups($headline_group, $svg, color) {
    var head_points = get_headline_points($headline_group, $svg);
    var svg_html = '';
    for (var i = 0; i < head_points.length; i++) {
        svg_html = svg_html + '<path d="' + head_points[i] + '" fill="none" stroke=' + color + ' stroke-width=3 />'
    }
    return svg_html;
}

function connect_sauce($svg) {
    var svg_offset = $svg.parent().offset().top;
    var left = $( window ).width() / 2;
    if(left >= 384){
        var $headlines = $('.connected');
        var points = "M " + left + ' ' + ($headlines.eq(0).offset().top + parseInt($headlines.eq(0).css('height').replace('px', '')) - svg_offset) +
            " L " + left + ' ' + ($headlines.eq(1).offset().top - svg_offset);
        return '<path d="' + points + '" fill="none" stroke="white" stroke-width=3 stroke-dasharray="18, 20"/>';
    } else {
        return '';
    }
}

function get_zigzag_points($piktos, $svg) {
    var svg_offset = $svg.parent().offset().top;
    var $first = $('#first_pikto');
    var points = "M " + ($(window).width() / 2) + ' ' + ($first.offset().top + parseInt($first.css('height').replace('px', '')) - svg_offset) + " L ";
    for (var i = 0; i < $piktos.length; i++) {
        points = points + ( ($piktos.eq(i).offset().left + 50) + " " + ($piktos.eq(i).offset().top + 50 - svg_offset) + " ");
    }
    return points;
}

function refresh_items_lines(){
    var $svg = $('#items_svg');
    var svg_html = connect_headline_groups($('#items_head'), $svg, 'white');
    svg_html = svg_html + connect_sauce($svg);
    $svg.html(svg_html);
}

function refresh_reasons_lines(){
    var $svg = $('#reasons_svg');
    var svg_html = connect_headline_groups($('#reasons_head'), $svg, 'black');
    var points = get_zigzag_points($('.pikto'), $svg);
    svg_html = svg_html + '<path d="' + points + '" fill="none" stroke=black stroke-width=3 stroke-dasharray="10, 12"/>';
    $svg.html(svg_html);
}

function refresh_svg() {
    refresh_items_lines();
    refresh_reasons_lines();
    setTimeout(function () {
        refresh_items_lines();
        refresh_reasons_lines();
    }, 400);

}


$(function () {
    refresh_svg();
    $(window).resize(function (event) {
        refresh_svg()
    });
});