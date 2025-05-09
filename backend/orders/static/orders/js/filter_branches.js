(function($) {
    $(document).ready(function() {
        var customerField = $('#id_customer');
        var branchField = $('#id_branch');

        function loadBranches(customerId, selectedBranchId) {
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
                            var option = $('<option></option>').attr('value', branch.id).text(branch.name);
                            if (branch.id == selectedBranchId) {
                                option.attr('selected', 'selected');
                            }
                            branchField.append(option);
                        });
                    }
                });
            } else {
                branchField.append($('<option></option>').attr('value', '').text('---------'));
            }
        }

        // On customer change
        customerField.change(function() {
            loadBranches($(this).val());
        });

        // Trigger it on page load with existing values
        var existingCustomerId = customerField.val();
        var existingBranchId = branchField.val();
        if (existingCustomerId) {
            loadBranches(existingCustomerId, existingBranchId);
        }
    });
})(django.jQuery);
