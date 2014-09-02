import logging
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


LOGGER = logging.getLogger("djinn_auth")


class AuthBackend(object):

    # We support object based permissions
    #
    supports_object_permissions = True
    supports_anonymous_user = False

    def authenticate(self, username=None, password=None):

        return None

    def get_user(self, user_id):

        return None

    def has_perm(self, user, permission, obj=None):

        """ Find out whether the user has a given permission. This is
        a potentially 'heavy' operation, given the role based auth
        that we have.

        A user can have a permission in general (obj=None) if:
          1. the user has a global role that holds the permission
          2. the user is part of a group that has a global role that holds the
             permission

        When an object is provided, the user can FURTHERMORE have a permission
        if:
          3. the user has a local role on the object
          4. the user is part of a group that has a local role on the object

        Some heuristics are in place to try and determine this in a
        smart way. We first check on the 'user' role. If this holds
        the permission, return. If not, check ownership...

        """

        if user.is_anonymous():
            return False

        return self._check_all_permissions(user, permission, obj=obj)

    def _check_all_permissions(self, user, perm, obj=None):

        """ Go find the actual permission, then loop over it's roles, users
        and groups. Check if the user has the global role, the role
        locally if obj is provided, or is in a group with that
        permission.
        """

        perm_app, perm_name = perm.split(".")

        _perm = Permission.objects.get(codename=perm_name)

        # Check whether the user is in the permission's user set
        #
        if _perm.user_set.filter(username=user.username).exists():
            return True

        perm_group_ids = perm.group_set.all().values_list('id', flat=True)

        # Check whether the user and the permission share any groups
        #
        if _perm.group_set.filter(pk__in=perm_group_ids):
            return True

        # Now check on the roles. Start with global roles
        #
        perm_role_ids = perm.role_set.all().values_list('id', flat=True)

        if not obj or getattr(obj, "acquire_global_roles", True):

            if user.globalrole_set.filter(role__id__in=perm_role_ids).exists():
                return True

        # Now go for local roles if need be
        #
        if obj:

            ctype = ContentType.objects.get_for_model(obj)

            if user.localrole_set.filter(
                    role__id__in=perm_role_ids,
                    instance_id=obj.id,
                    instance_ct=ctype
            ).exists():
                return True

        return False