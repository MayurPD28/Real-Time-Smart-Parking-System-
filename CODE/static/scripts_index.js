document.getElementById('bookSlot').onclick = function() {
    document.getElementById('otpModal').style.display = 'block';
};

document.getElementsByClassName('close')[0].onclick = function() {
    document.getElementById('otpModal').style.display = 'none';
};

function verifyOTP() {
    var otp = document.getElementById('otpInput').value;
    if (otp === '0000') {
        window.location.href = 'slotmap.html';
    } else {
        alert('Incorrect OTP, please try again.');
    }
}
