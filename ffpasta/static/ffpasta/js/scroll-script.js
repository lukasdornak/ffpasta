var page = 0;
var item = '';
var readyToScroll = true;
var hashChanged = false;
var documentScrollTop = 0;
var ogOverride;


function nextCheck(){
    if(hashChanged){
        hashCheck();
    }
}

function hashCheck(){
    hashChanged = false;
    if ( $items.index($( window.location.hash.replace('#','#id-') )) !== -1 ) {
        var newItem = window.location.hash.replace('#', '');
        getItem(newItem);
        if( !item ) {
            item = newItem;
            showItem();
        } else {
            item = newItem;
        }
        page = -1;

    } else {
        var newPage = $pages.index($( window.location.hash.replace('#','#id-') ));
        if(newPage === -1){
            window.location.hash = $pages.eq(0).attr('id').replace('id-', '');
            return 0;
        }
        if (page === -1){
            hideItem();
            item = '';
            if(newPage < 2) {
                window.scrollTo(0, documentScrollTop);
                page = getScrolledPage();
                window.location.hash = $pages.eq(page).attr('id').replace('id-', '');
                return 0;
            }
        }
        if( newPage !== page ){
            if(readyToScroll){
                readyToScroll = false;
                page = newPage;
                scrollToPage();
            } else {
                hashChanged = true;
            }
        }
    }
}

function getItem(item){
    $.ajax({
        url: 'ajax/' + item + '/',
        cache: true
    }).done(function( response ) {
        ogOverride = JSON.parse(response);
        $("#modal").html( ogOverride['body'] ).addClass('shown');
    });
}

function getScrolledPage(){
    for(p=$pages.length-1, len=0; p>=len; p-- ){
        if( $(document).scrollTop() > ($pages.eq(p).offset().top - head) ){
            return p;
        }
    }
}

function scrollToPage(){
    $('html, body').animate({
        scrollTop: $pages.eq(page).offset().top - head + 5
    }, 800);
    $('body').promise().done(function() {
        readyToScroll = true;
        nextCheck();
    });
}

function pageCheck(){
    var scrolled = getScrolledPage();
    if(page!=scrolled){
        page = scrolled;
        window.location.hash = $pages.eq(page).attr('id').replace('id-', '');
    }
}

function showItem(){
    readyToScroll = false;
    if ( $(document).scrollTop() < $pages.eq(1).offset().top ) {
        window.scrollTo(0, $pages.eq(1).offset().top - head + 5);
    }
    documentScrollTop = $(document).scrollTop();
    $('#menu_button').removeClass('cross');
    $('nav').addClass('hidden');
    $('body').addClass('stop').css('top', -documentScrollTop + 'px');
    $('#modal').removeClass('hidden');
}

function hideItem(){
    $('body').removeClass('stop');
    window.scrollTo(0, documentScrollTop);
    $('#modal').removeClass('shown');
    setTimeout(function () {
        $('#modal').addClass('hidden');
        readyToScroll = true;
    }, 500)
}

function shareOverrideOGMeta(){
	FB.ui({
		method: 'share_open_graph',
		action_type: 'og.likes',
		action_properties: JSON.stringify({
			object: {
				'og:url': ogOverride['ogUrl'],
				'og:title': ogOverride['ogTitle'],
				'og:type': ogOverride['ogtype'],
				'og:description': ogOverride['ogDescription'],
				'og:image': ogOverride['ogImage']
			}
		})
	},
	function (response) {
	// Action after response
	});
}

$(function(){
    $pages = $('section');
    $items = $('.item');
    head = 107;
    hashCheck();
    $(window).on('hashchange', function(event) {
        hashCheck();
    });
    $(document).bind('scroll', function(event) {
        if(readyToScroll && !item){
            pageCheck();
        } else {
            event.preventDefault();
        }
    });
    $('#menu_button').click(function(event) {
        $('#menu_button').toggleClass('cross');
        $('nav').toggleClass('hidden');
    });
    $('nav a').click(function(event) {
        $('#menu_button').removeClass('cross');
        $('nav').addClass('hidden');
    });
})
