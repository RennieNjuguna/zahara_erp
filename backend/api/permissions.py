from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.created_by == request.user


class IsStaffOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow staff members to edit objects.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any authenticated request,
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # Write permissions are only allowed to staff members.
        return request.user and request.user.is_authenticated and request.user.is_staff


class IsOwnerOrStaff(permissions.BasePermission):
    """
    Custom permission to only allow owners or staff to access objects.
    """

    def has_object_permission(self, request, view, obj):
        # Staff members have full access
        if request.user.is_staff:
            return True

        # Owners can access their own objects
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user

        # For objects without created_by field, allow read access to authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        return False


class PaymentPermission(permissions.BasePermission):
    """
    Custom permission for payment-related operations.
    Only staff can create/edit payments, but customers can view their own.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff can do anything
        if request.user.is_staff:
            return True

        # Non-staff users can only read
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff can do anything
        if request.user.is_staff:
            return True

        # Customers can only view their own payments
        if hasattr(obj, 'customer') and request.method in permissions.SAFE_METHODS:
            return obj.customer.created_by == request.user if hasattr(obj.customer, 'created_by') else False

        return False


class OrderPermission(permissions.BasePermission):
    """
    Custom permission for order-related operations.
    Staff can do anything, customers can view their own orders.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff can do anything
        if request.user.is_staff:
            return True

        # Non-staff users can only read
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff can do anything
        if request.user.is_staff:
            return True

        # Customers can only view their own orders
        if hasattr(obj, 'customer') and request.method in permissions.SAFE_METHODS:
            return obj.customer.created_by == request.user if hasattr(obj.customer, 'created_by') else False

        return False


class CustomerPermission(permissions.BasePermission):
    """
    Custom permission for customer-related operations.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff can do anything
        if request.user.is_staff:
            return True

        # Non-staff users can only read
        return request.method in permissions.SAFE_METHODS


class ExpensePermission(permissions.BasePermission):
    """
    Custom permission for expense-related operations.
    Only staff can manage expenses.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Only staff can manage expenses
        return request.user.is_staff

