// Existing branch filtering functionality
document.addEventListener('DOMContentLoaded', function() {
    const customerSelect = document.getElementById('id_customer');
    const branchSelect = document.getElementById('id_branch');

    if (customerSelect && branchSelect) {
        // Initial setup - clear branches if no customer selected
        if (!customerSelect.value) {
            branchSelect.innerHTML = '<option value="">---------</option>';
            branchSelect.disabled = true;
        }

        customerSelect.addEventListener('change', function() {
            const customerId = this.value;
            if (customerId) {
                // Clear and disable branch select while loading
                branchSelect.innerHTML = '<option value="">Loading...</option>';
                branchSelect.disabled = true;

                // Use the admin custom URL
                fetch(`/admin/orders/order/get-branches/?customer_id=${customerId}`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(branches => {
                        branchSelect.innerHTML = '<option value="">---------</option>';
                        branches.forEach(branch => {
                            const option = document.createElement('option');
                            option.value = branch.id;
                            option.textContent = branch.name;
                            branchSelect.appendChild(option);
                        });
                        branchSelect.disabled = false;
                    })
                    .catch(error => {
                        console.error('Error loading branches:', error);
                        branchSelect.innerHTML = '<option value="">Error loading branches</option>';
                        branchSelect.disabled = true;
                    });
            } else {
                branchSelect.innerHTML = '<option value="">---------</option>';
                branchSelect.disabled = true;
            }
        });
    }
});

// New functionality for auto-filling stem length and price defaults
document.addEventListener('DOMContentLoaded', function() {
    // Handle product selection changes in OrderItem inlines
    document.addEventListener('change', function(e) {
        if (e.target.classList.contains('product-select')) {
            const row = e.target.closest('tr');
            const stemLengthInput = row.querySelector('.stem-length-input');
            const priceInput = row.querySelector('.price-input');
            const customerSelect = document.getElementById('id_customer');

            if (stemLengthInput && customerSelect && customerSelect.value) {
                const productId = e.target.value;
                const customerId = customerSelect.value;

                if (productId) {
                    // First, try to get defaults from CustomerOrderDefaults
                    fetch('/admin/orders/order/get-defaults/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/x-www-form-urlencoded',
                            'X-CSRFToken': getCookie('csrftoken')
                        },
                        body: `customer_id=${customerId}&product_id=${productId}`
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            stemLengthInput.value = data.stem_length_cm;
                            // Trigger change event to update price
                            stemLengthInput.dispatchEvent(new Event('change'));
                        }
                    })
                    .catch(error => {
                        console.error('Error loading defaults:', error);
                    });
                }
            }
        }

        // Handle stem length changes to auto-populate price
        if (e.target.classList.contains('stem-length-input')) {
            const row = e.target.closest('tr');
            const productSelect = row.querySelector('.product-select');
            const priceInput = row.querySelector('.price-input');
            const customerSelect = document.getElementById('id_customer');

            if (productSelect && priceInput && customerSelect && customerSelect.value) {
                const productId = productSelect.value;
                const customerId = customerSelect.value;
                const stemLength = e.target.value;

                if (productId && stemLength) {
                    // Get pricing for this customer-product-stem length combination
                    fetch(`/admin/orders/order/get-pricing/?customer_id=${customerId}&product_id=${productId}&stem_length=${stemLength}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.success && data.price) {
                                priceInput.value = data.price;
                                // Trigger change event to update calculations
                                priceInput.dispatchEvent(new Event('change'));
                            } else {
                                // Clear price if no pricing found
                                priceInput.value = '';
                            }
                        })
                        .catch(error => {
                            console.error('Error loading pricing:', error);
                            priceInput.value = '';
                        });
                }
            }
        }
    });

    // Function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
