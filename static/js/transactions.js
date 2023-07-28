$("#navbar>div>div>ul>li>a.active").removeClass("active");
$("#transactions_nav").addClass("active");

const socket = io.connect(`https://${window.location.hostname}/transactions`);

socket.on('connect', function() {
})

var tableBody = document.getElementById("transactions_table_body");
var pageNumber = 1;
var isLoadingData = false;

function loadMoreData() {
    if (isLoadingData) {
      return;
    }
    isLoadingData = true;
    pageNumber++;
    socket.emit('get_transactions', data1=(pageNumber));
}

socket.on('transactions_data', function(data) {
    isLoadingData = false;
    if (data.length === 0) {
      return;
    }
    for (var i = 0; i < data.length; i++) {
        var row = document.createElement("tr");
      
        var dateCell = document.createElement("td");
        dateCell.innerHTML = data[i].date;
        row.appendChild(dateCell);

        var senderCell = document.createElement("td");
        senderCell.innerHTML = data[i].from;
        row.appendChild(senderCell);

        var recipientCell = document.createElement("td");
        recipientCell.innerHTML = data[i].to;
        row.appendChild(recipientCell);

        var descCell = document.createElement("td");
        descCell.innerHTML = data[i].desc;
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
});

$(document).ready(function () {
    socket.emit('get_transactions', data1=(pageNumber))
});