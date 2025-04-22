(function($) {
    $(document).ready(function() {
        $('#id_customer').change(function() {
            var customerId = $(this).val();
            var url = window.location.href;

            $.ajax({
                url: '/admin/get-branches/',
                data: {
                    'customer_id': customerId
                },
                success: function(data) {
                    var branchField = $('#id_branch');
                    branchField.empty();

                    if (data.branches.length === 0) {
                        branchField.append('<option value="">No branches</option>');
                    } else {
                        branchField.append('<option value="">---------</option>');
                        for (var i = 0; i < data.branches.length; i++) {
                            var branch = data.branches[i];
                            branchField.append('<option value="' + branch.id + '">' + branch.name + '</option>');
                        }
                    }
                }
            });
        });
    });
})(django.jQuery);
