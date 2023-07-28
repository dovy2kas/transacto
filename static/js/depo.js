$("#navbar>div>div>ul>li>a.active").removeClass("active");
$("#depo_nav").addClass("active");

//disable image dragging for the cards
$('img').on('dragstart', function(event) { event.preventDefault(); });

const notification_container = document.getElementById('notification_container');

function send_notification(message) {
    $('.modal').modal('hide');
    notification_container.innerHTML += '<div class="toast fade show mb-2" id="myToast"><div class="toast-header"><strong class="me-auto"><i class="bi-gift-fill"></i> Notification</strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div><div class="toast-body" id="notification">'+ message + '</div></div>'
}

const socket = io.connect(`https://${window.location.hostname}/main`);
socket.on('connect', function() {
});

socket.on('send_notification', function(message) {
    send_notification(message);
});

socket.on('paysera_payment_direction', function(url) {
    window.open(url, '_blank');
});

paysera_card = document.getElementById("paysera_card");
paypal_card = document.getElementById("paypal_card");

paypal_withdraw_card_status = document.getElementById("paypal_withdraw_card_status");
bank_withdraw_card = document.getElementById("bank_withdraw_card");

var paypal_card_status = 0
var paypal_withdraw_card_status = 0
var paysera_card_status = 0

var bank_withdraw_card_status = 0

$('#paypal_card').click(function () {
    paysera_card.classList.remove("visited");
    paysera_card_status = 0;
    if (paypal_card_status == 0) {
        paypal_card.classList.add("visited");
        paypal_card_status = 1;
    } else {
        paypal_card.classList.remove("visited");
        paypal_card_status = 0;
    }
    return false;
});

$('#paysera_card').click(function () {
    paypal_card.classList.remove("visited");
    paypal_card_status = 0
    if (paysera_card_status == 0) {
        paysera_card.classList.add("visited");
        paysera_card_status = 1;
    } else {
        paysera_card.classList.remove("visited");
        paysera_card_status = 0;
    }
    return false;
});

$('#bank_withdraw_card').click(function () {
    paypal_withdraw_card.classList.remove("visited");
    paypal_withdraw_card_status = 0

    if (bank_withdraw_card_status == 0) {
        bank_withdraw_card.classList.add("visited");
        bank_withdraw_card_status = 1;
    } else {
        bank_withdraw_card.classList.remove("visited");
        bank_withdraw_card_status = 0;
    }
    return false;
});

$('#paypal_withdraw_card').click(function () {
    bank_withdraw_card.classList.remove("visited");
    bank_withdraw_card_status = 0;

    if (paypal_withdraw_card_status == 0) {
        paypal_withdraw_card.classList.add("visited");
        paypal_withdraw_card_status = 1;
    } else {
        paypal_withdraw_card.classList.remove("visited");
        paypal_withdraw_card_status = 0;
    }
    return false;
});

function paypal_withdrawal() {
    var amount = document.getElementById('confirm_paypal_withdrawal_amount').value;
    socket.emit('paypal_payout', data1=(amount));
}

function paysera_deposit() {
    var amount = document.getElementById('confirm_paysera_amount').value;
    socket.emit('paysera_deposit', data1=(amount));
}

function deposit_proceed() {
    var amount = document.getElementById('depo_amount').value;
    
    if (paypal_card_status == 1) {
        document.getElementById('confirm_paypal_amount').value = amount;
        $('#paypal_modal').modal('show');
    } else {
        document.getElementById('confirm_paysera_amount').value = amount;
        $('#paysera_modal').modal('show');
    }
}

function withdrawal_proceed() {
    var amount = document.getElementById('withdraw_amount').value;
    document.getElementById('confirm_paypal_withdrawal_amount').value = amount;
    $('#paypal_withdrawal_modal').modal('show');
}