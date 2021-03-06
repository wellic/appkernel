from typing import Type

import jwt
from flask import request
from flask_babel import _, lazy_gettext as _l

import appkernel
from appkernel import iam
from appkernel.configuration import config


def check_token(jwt_token) -> dict:
    return jwt.decode(jwt_token, config.public_key)


def __has_current_subject_authority(token: dict, authority):
    if not isinstance(authority, iam.CurrentSubject):
        raise TypeError('This method required authority of type {}.'.format(iam.CurrentSubject.__name__))
    subject = token.get('sub', None)
    binding_id = request.view_args.get(authority.view_arg)
    if not subject or not binding_id:
        return False
    return subject == binding_id


def __get_required_permissions():
    endpoint_config = config.service_registry.get(request.endpoint)
    perms = endpoint_config.get_required_permission(request.method, request.endpoint)

    if perms:
        if isinstance(perms, iam.Permission):
            perms = [perms]
        elif not isinstance(perms, list):
            raise AttributeError
    return perms


def __contains(required_permissions: list, permission_type: Type):
    contained_permissions = [permission for permission in required_permissions if
                             isinstance(permission, permission_type)]
    return len(contained_permissions) > 0


def __split_to_roles_and_authorities(required_permissions: list):
    required_roles = set()
    required_authorities = set()
    for item in required_permissions:
        if isinstance(item, iam.Role):
            required_roles.add(item.name)
        elif isinstance(item, iam.Authority):
            required_authorities.add(item)
    return required_roles, required_authorities


def __has_required_authority(required_authorities: list, token: dict):
    if not required_authorities or len(required_authorities) == 0:
        return False
    else:
        for required_authority in required_authorities:
            check_authority = authority_evaluators.get(required_authority.__class__.__name__)
            has_required_authority = check_authority(token, required_authority)
            if has_required_authority:
                return True
    return False


authority_evaluators = {
    iam.CurrentSubject.__name__: __has_current_subject_authority
}


def authorize_request():
    app_engine = appkernel.Service.app_engine
    required_permissions = __get_required_permissions()

    if __contains(required_permissions, iam.Denied):
        return app_engine.create_custom_error(403, _('Not allowed to access method.'))

    if __contains(required_permissions, iam.Anonymous):
        return

    authorisation_header = request.headers.get('Authorization')
    if not authorisation_header:
        return app_engine.create_custom_error(401, _('The authorisation header is missing.'))
    try:
        token = check_token(authorisation_header.split(' ')[1])
        required_roles, required_authorities = __split_to_roles_and_authorities(required_permissions)

        missing_required_role = len(required_roles.intersection(set(token.get('roles', [])))) == 0
        missing_required_authority = not __has_required_authority(required_authorities, token)

        if missing_required_role and missing_required_authority:
            return app_engine.create_custom_error(403, _('The required permission is missing.'))
    except AttributeError:
        return app_engine.create_custom_error(401, _('The permission type is not supported.'))
    except Exception as exc:
        return app_engine.create_custom_error(403, str(exc))
