$("#navbar>div>div>ul>li>a.active").removeClass("active");
$("#profile_nav").addClass("active");

const notification_container = document.getElementById('notification_container');
var auth_secret;

function send_notification(message) {
    notification_container.innerHTML += '<div class="toast fade show mb-2" id="myToast"><div class="toast-header"><strong class="me-auto"><i class="bi-gift-fill"></i> Notification</strong><button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button></div><div class="toast-body" id="notification">'+ message + '</div></div>'
}

const socket = io.connect(`https://${window.location.hostname}/profile`);
socket.on('connect', function() {
    socket.emit('generate_2fa');
});

socket.on('send_notification', function(message) {
    send_notification(message);
});

socket.on('load_qr', function(username) {
    document.getElementById('qr-container').innerHTML = '<img src="static/img/' + username + '_qr.png" alt="QR Code" style="max-width: 100%;">'
});

socket.on('remove_2fa_button', function() {
    document.getElementById('2fa_button').remove();
})

function confirm_2fa() {
    var totp_code = document.getElementById('totp_code').value;
    socket.emit('confirm_2fa', data1=(totp_code));
}

function change_password() {
    var current_password = document.getElementById('current_password').value;
    var new_password = document.getElementById('new_password').value;
    var repeat_password = document.getElementById('repeat_password').value;
    socket.emit('change_password', data1=(current_password), data2=(new_password), data3=(repeat_password));
}

function change_email() {
    var new_email = document.getElementById('change_email').value;
    socket.emit('change_email', data1=(new_email))
}

function activate_email_change() {
    $('#change_email').removeAttr("disabled");
    document.getElementById('change_email_button').setAttribute("onclick", "javascript: change_email();");
}

$("#profileImage").click(function(e) {
    $("#imageUpload").click();
});

function fasterPreview( uploader ) {
    if ( uploader.files && uploader.files[0] ){
          $('#profileImage').attr('src', 
             window.URL.createObjectURL(uploader.files[0]) );
    }
}

$("#imageUpload").change(function(){
    fasterPreview( this );
});

//Password strenght checker
let state = false;
let password = document.getElementById("new_password");
let passwordStrength = document.getElementById("password-strength");
let lowUpperCase = document.querySelector(".low-upper-case i");
let number = document.querySelector(".one-number i");
let specialChar = document.querySelector(".one-special-char i");
let eightChar = document.querySelector(".eight-character i");

password.addEventListener("keyup", function(){
    let pass = document.getElementById("new_password").value;
    checkStrength(pass);
});

function checkStrength(password) {
    let strength = 0;

    if (password.match(/([a-z].*[A-Z])|([A-Z].*[a-z])/)) {
        strength += 1;
        lowUpperCase.classList.remove('fa-circle');
        lowUpperCase.classList.add('fa-check');
    } else {
        lowUpperCase.classList.add('fa-circle');
        lowUpperCase.classList.remove('fa-check');
    }

    if (password.match(/([0-9])/)) {
        strength += 1;
        number.classList.remove('fa-circle');
        number.classList.add('fa-check');
    } else {
        number.classList.add('fa-circle');
        number.classList.remove('fa-check');
    }

    if (password.match(/([!,%,&,@,#,$,^,*,?,_,~])/)) {
        strength += 1;
        specialChar.classList.remove('fa-circle');
        specialChar.classList.add('fa-check');
    } else {
        specialChar.classList.add('fa-circle');
        specialChar.classList.remove('fa-check');
    }

    if (password.length > 7) {
        strength += 1;
        eightChar.classList.remove('fa-circle');
        eightChar.classList.add('fa-check');
    } else {
        eightChar.classList.add('fa-circle');
        eightChar.classList.remove('fa-check');   
    }
    
    if (strength < 2) {
        passwordStrength.classList.remove('progress-bar-warning');
        passwordStrength.classList.remove('progress-bar-success');
        passwordStrength.classList.add('progress-bar-danger');
        passwordStrength.style = 'width: 10%';
    } else if (strength == 3) {
        passwordStrength.classList.remove('progress-bar-success');
        passwordStrength.classList.remove('progress-bar-danger');
        passwordStrength.classList.add('progress-bar-warning');
        passwordStrength.style = 'width: 60%';
    } else if (strength == 4) {
        passwordStrength.classList.remove('progress-bar-warning');
        passwordStrength.classList.remove('progress-bar-danger');
        passwordStrength.classList.add('progress-bar-success');
        passwordStrength.style = 'width: 100%';
    }
}