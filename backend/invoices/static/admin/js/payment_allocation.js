(function($) {
    $(document).ready(function() {
        var paymentField = $('#id_payment');
        var orderField = $('#id_order');

        function loadOrders(paymentId) {
            orderField.empty();
            orderField.append($('<option></option>').attr('value', '').text('---------'));

            if (paymentId) {
                $.ajax({
                    url: '/orders/get-orders/',
                    data: {
                        'payment_id': paymentId
                    },
                    dataType: 'json',
                    success: function(data) {
                        $.each(data, function(index, order) {
                            var option = $('<option></option>')
                                .attr('value', order.id)
                                .text(order.invoice_code + ' - ' + order.total_amount + ' ' + order.currency + ' (Outstanding: ' + order.outstanding_amount + ')');
                            orderField.append(option);
                        });
                    },
                    error: function() {
                        console.error('Error loading orders');
                    }
                });
            }
        }

        // On payment change
        paymentField.change(function() {
            loadOrders($(this).val());
        });

        // Trigger it on page load with existing values
        var existingPaymentId = paymentField.val();
        if (existingPaymentId) {
            loadOrders(existingPaymentId);
        }
    });
})(django.jQuery);
