$(document).ready(function() {
    var bookedSlot; // Variable to store the currently booked slot
    var interval; // Variable to store the interval

    $('.slot.available').click(function() {
        var slot = this;

        // Check if the slot is available and no slot is currently booked
        if ($(this).hasClass('available') && !bookedSlot) {
            // Ask user if they want to book the slot for 10 minutes
            if (confirm("Do you want to book this slot for 10 minutes?")) {
                // Remove available class and add booked class
                $(this).removeClass('available').addClass('booked');
                bookedSlot = $(this); // Set the currently booked slot
                var counter = 600; // 10 minutes in seconds
                $(this).text('10:00');

                // Start the timer
                interval = setInterval(function() {
                    counter--;
                    var minutes = Math.floor(counter / 60);
                    var seconds = counter % 60;
                    $(slot).text(minutes + ':' + (seconds < 10 ? '0' : '') + seconds);

                    // If the timer reaches 0, clear the interval and reset the slot status
                    if (counter <= 0) {
                        clearInterval(interval);
                        $(slot).text($(slot).attr('id')); // Reset to slot number with letter prefix
                        $(slot).removeClass('booked').addClass('available');
                        bookedSlot = null; // Reset the currently booked slot
                    }
                }, 1000);
            }
        } else if ($(this).hasClass('booked') && $(this).is(bookedSlot)) { // Check if the slot is booked and is the currently booked slot
            // Ask user if they want to clear this booking
            if (confirm("Do you want to clear this booking?")) {
                // Reset the timer to 10 minutes
                $(this).text($(slot).attr('id')); // Reset to slot number with letter prefix

                // Clear the interval
                clearInterval(interval);

                // Make the slot available again
                $(this).removeClass('booked').addClass('available');
                bookedSlot = null; // Reset the currently booked slot
            }
        } else {
            // Inform the user that they can only book one slot at a time
            alert("You can only book one slot at a time. Please clear your current booking before booking another slot.");
        }
    });
});
