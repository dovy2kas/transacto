$("#navbar>div>div>ul>li>a.active").removeClass("active");
$("#dashboard_nav").addClass("active");

const notification_container = document.getElementById('notification_container');
const button = document.getElementById("confirm_payment");
const balance_wrapper = document.getElementById('balance_wrapper');
let timeoutId;

function send_notification(message) {
    notification_container.innerHTML += '<div class="toast fade show mb-2" id="myToast"><div class="toast-header"><strong class="me-auto"><i class="bi-gift-fill"></i> Notification</strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div><div class="toast-body" id="notification">'+ message + '</div></div>'
}

function send_money() {
    var recipient = document.getElementById('send_recipient').value;
    var amount = document.getElementById('send_amount').value;
    var description = document.getElementById('send_description').value;
    var totp_code = document.getElementById('confirm_send_totp').value;

    socket.emit('send_money', data1=(recipient), data2=(amount), data3=(description), data4=(totp_code))
}

function update_transactions(data) {
    var tableBody = document.getElementById("transaction_table_body");
  
    tableBody.innerHTML = "";
  
    for (var i = 0; i < data.length; i++) {
        var row = document.createElement("tr");
  
        var dateCell = document.createElement("td");
        dateCell.innerHTML = data[i].date;
        row.appendChild(dateCell);
  
        var descCell = document.createElement("td");
        descCell.innerHTML = data[i].description;
        row.appendChild(descCell);
  
        var amountCell = document.createElement("td");
        if (data[i].amount > 0) {
            amountCell.style.color = '#50C878';
            amountCell.style.fontWeight = 'bold';
            amountCell.innerHTML = "+€" + data[i].amount;
        } else {
            amountCell.style.color = '#FF0000';
            amountCell.style.fontWeight = 'bold';
            amountCell.innerHTML = "-€" + data[i].amount * -1;
        }
        row.appendChild(amountCell);
  
        tableBody.appendChild(row);
    }
}
  
const socket = io.connect(`https://${window.location.hostname}/dashboard`);
socket.on('connect', function() {
    socket.emit('update_transactions');
});

socket.on('update_balance', function(balance) {
    balance_wrapper.innerHTML = '€' + balance;
});

socket.on('update_transactions', function(data) {
    update_transactions(data);
});

socket.on('send_notification', function(message) {
    send_notification(message);
});

socket.on('send_success', function() {
    $('#send_modal').modal('hide');
    send_notification('Payment successfully sent!');
});

socket.on('send_failed', function(message) {
    $('#send_modal').modal('hide');
    send_notification(message);
});

function payment_confirmation_menu() {
    var recipient = document.getElementById('send_recipient').value;
    var amount = document.getElementById('send_amount').value;
    var description = document.getElementById('send_description').value;

    document.getElementById('confirm_send_recipient').value = recipient;
    document.getElementById('confirm_send_amount').value = amount;
    document.getElementById('confirm_send_description').value = description;
}

button.addEventListener("mousedown", function() {
    
    button.classList.add("loading");
    timeoutId = setTimeout(function() {
        send_money();
        button.classList.remove("loading");
        button.classList.remove("button_animation");
        void button.offsetWidth;
        button.classList.add("button_animation");
    }, 3000);
});

button.addEventListener("touchstart", function() {
    
    button.classList.add("loading");
    timeoutId = setTimeout(function() {
        send_money();
        button.classList.remove("loading");
        button.classList.remove("button_animation");
        void button.offsetWidth;
        button.classList.add("button_animation");
    }, 3000);
});

button.addEventListener("touchend", function() {
    clearTimeout(timeoutId);
    button.classList.remove("loading");
    button.classList.remove("button_animation");
    void button.offsetWidth;
    button.classList.add("button_animation");
});

button.addEventListener("mouseup", function() {
  clearTimeout(timeoutId);
  button.classList.remove("loading");
  button.classList.remove("button_animation");
  void button.offsetWidth;
  button.classList.add("button_animation");
  
});

if (message != "Empty") {
    send_notification(message);
}
