(function($) {
    $(document).ready(function() {
        $('#id_customer').change(function() {
            var customerId = $(this).val();
            var branchField = $('#id_branch');

            // Clear current options
            branchField.empty();

            if (customerId) {
                $.ajax({
                    url: '/orders/get-branches/',
                    data: {
                        'customer_id': customerId
                    },
                    dataType: 'json',
                    success: function(data) {
                        branchField.append($('<option></option>').attr('value', '').text('---------'));
                        $.each(data, function(index, branch) {
                            branchField.append($('<option></option>').attr('value', branch.id).text(branch.name));
                        });
                    }
                });
            } else {
                branchField.append($('<option></option>').attr('value', '').text('---------'));
            }
        });
    });
})(django.jQuery);
