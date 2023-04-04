# Copyright 2018 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# patched by Intuitem to perform patch before create

import re
import os

import yaml

from kubernetes import client

DEFAULT_DELETION_BODY = client.V1DeleteOptions(
    propagation_policy="Background",
    grace_period_seconds=5,
)

UPPER_FOLLOWED_BY_LOWER_RE = re.compile('(.)([A-Z][a-z]+)')
LOWER_OR_NUM_FOLLOWED_BY_UPPER_RE = re.compile('([a-z0-9])([A-Z])')


def create_from_yaml(
        k8s_client,
        yaml_file=None,
        yaml_objects=None,
        verbose=False,
        namespace="default",
        **kwargs):
    """
    Perform an action from a yaml file. Pass True for verbose to
    print confirmation information.
    Input:
    yaml_file: string. Contains the path to yaml file.
    k8s_client: an ApiClient object, initialized with the client args.
    yaml_objects: List[dict]. Optional list of YAML objects; used instead
        of reading the `yaml_file`. Default is None.
    verbose: If True, print confirmation from the create action.
        Default is False.
    namespace: string. Contains the namespace to create all
        resources inside. The namespace must preexist otherwise
        the resource creation will fail. If the API object in
        the yaml file already contains a namespace definition
        this parameter has no effect.
    Available parameters for creating <kind>:
    :param async_req bool
    :param bool include_uninitialized: If true, partially initialized
        resources are included in the response.
    :param str pretty: If 'true', then the output is pretty printed.
    :param str dry_run: When present, indicates that modifications
        should not be persisted. An invalid or unrecognized dryRun
        directive will result in an error response and no further
        processing of the request.
        Valid values are: - All: all dry run stages will be processed
    Returns:
        The created kubernetes API objects.
    Raises:
        FailToCreateError which holds list of `client.rest.ApiException`
        instances for each object that failed to create.
    """

    def create_with(objects):
        failures = []
        k8s_objects = []
        for yml_document in objects:
            if yml_document is None:
                continue
            try:
                created = create_from_dict(k8s_client, yml_document, verbose,
                                           namespace=namespace,
                                           **kwargs)
                k8s_objects.append(created)
            except FailToCreateError as failure:
                failures.extend(failure.api_exceptions)
        if failures:
            raise FailToCreateError(failures)
        return k8s_objects

    if yaml_objects:
        yml_document_all = yaml_objects
        return create_with(yml_document_all)
    elif yaml_file:
        with open(os.path.abspath(yaml_file)) as f:
            yml_document_all = yaml.safe_load_all(f)
            return create_with(yml_document_all)
    else:
        raise ValueError(
            'One of `yaml_file` or `yaml_objects` arguments must be provided')


def create_from_dict(k8s_client, data, verbose=False, namespace='default',
                     **kwargs):
    """
    Perform an action from a dictionary containing valid kubernetes
    API object (i.e. List, Service, etc).
    Input:
    k8s_client: an ApiClient object, initialized with the client args.
    data: a dictionary holding valid kubernetes objects
    verbose: If True, print confirmation from the create action.
        Default is False.
    namespace: string. Contains the namespace to create all
        resources inside. The namespace must preexist otherwise
        the resource creation will fail. If the API object in
        the yaml file already contains a namespace definition
        this parameter has no effect.
    Returns:
        The created kubernetes API objects.
    Raises:
        FailToCreateError which holds list of `client.rest.ApiException`
        instances for each object that failed to create.
    """
    # If it is a list type, will need to iterate its items
    api_exceptions = []
    k8s_objects = []

    if "List" in data["kind"]:
        # Could be "List" or "Pod/Service/...List"
        # This is a list type. iterate within its items
        kind = data["kind"].replace("List", "")
        for yml_object in data["items"]:
            # Mitigate cases when server returns a xxxList object
            # See kubernetes-client/python#586
            if kind != "":
                yml_object["apiVersion"] = data["apiVersion"]
                yml_object["kind"] = kind
            try:
                created = create_from_yaml_single_item(
                    k8s_client, yml_object, verbose, namespace=namespace,
                    **kwargs)
                k8s_objects.append(created)
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        # This is a single object. Call the single item method
        try:
            created = create_from_yaml_single_item(
                k8s_client, data, verbose, namespace=namespace, **kwargs)
            k8s_objects.append(created)
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    # In case we have exceptions waiting for us, raise them
    if api_exceptions:
        raise FailToCreateError(api_exceptions)

    return k8s_objects


def create_from_yaml_single_item(
        k8s_client, yml_object, verbose=False, **kwargs):
    group, _, version = yml_object["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    # Only replace the last instance
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    fcn_to_call = "{0}{1}Api".format(group, version.capitalize())
    k8s_api = getattr(client, fcn_to_call)(k8s_client)
    # Replace CamelCased action_type into snake_case
    kind = yml_object["kind"]
    kind = UPPER_FOLLOWED_BY_LOWER_RE.sub(r'\1_\2', kind)
    kind = LOWER_OR_NUM_FOLLOWED_BY_UPPER_RE.sub(r'\1_\2', kind).lower()
    # Expect the user to create namespaced objects more often
    if hasattr(k8s_api, "create_namespaced_{0}".format(kind)):
        # Decide which namespace we are going to put the object in,
        # if any
        if "namespace" in yml_object["metadata"]:
            namespace = yml_object["metadata"]["namespace"]
            kwargs['namespace'] = namespace
        name = yml_object["metadata"]["name"]
        try:
            resp = getattr(k8s_api, "patch_namespaced_{0}".format(kind))(
                name=name, body=yml_object, **kwargs)
            print(f"patch {kind} {name}")
        except Exception as e:
            print(f"patch {kind} {name} failed", e)
            resp = getattr(k8s_api, "create_namespaced_{0}".format(kind))(
                body=yml_object, **kwargs)
            print(f"create {kind} {name}")
    else:
        kwargs.pop('namespace', None)
        try:
            resp = getattr(k8s_api, "patch_{0}".format(kind))(name, body=yml_object, **kwargs)
            print(f"patch {kind} {name}")
        except Exception as e:
            print(f"patch {kind} {name} failed", e)
            resp = getattr(k8s_api, "create_{0}".format(kind))(
                body=yml_object, **kwargs)
            print(f"create {kind} {name}")
    if verbose:
        msg = "{0} created.".format(kind)
        if hasattr(resp, 'status'):
            msg += " status='{0}'".format(str(resp.status))
        print(msg)
    return resp


class FailToCreateError(Exception):
    """
    An exception class for handling error if an error occurred when
    handling a yaml file.
    """

    def __init__(self, api_exceptions):
        self.api_exceptions = api_exceptions

    def __str__(self):
        msg = ""
        for api_exception in self.api_exceptions:
            msg += "Error from server ({0}): {1}".format(
                api_exception.reason, api_exception.body)
        return msg


###############################


def delete_from_yaml(
        k8s_client,
        yaml_file=None,
        yaml_objects=None,
        verbose=False,
        namespace="default",
        **kwargs):
    """
    Similar to create_from_yaml, but deletes object
    Raises:
        FailToDeleteError which holds list of `client.rest.ApiException`
    """

    def delete_with(objects):
        failures = []
        k8s_objects = []
        for yml_document in objects:
            if yml_document is None:
                continue
            try:
                created = delete_from_dict(k8s_client, yml_document, verbose,
                                           namespace=namespace,
                                           **kwargs)
                k8s_objects.append(created)
            except FailToDeleteError as failure:
                failures.extend(failure.api_exceptions)
        if failures:
            raise FailToDeleteError(failures)
        return k8s_objects

    if yaml_objects:
        yml_document_all = yaml_objects
        return delete_with(yml_document_all)
    elif yaml_file:
        with open(os.path.abspath(yaml_file)) as f:
            yml_document_all = yaml.safe_load_all(f)
            return delete_with(yml_document_all)
    else:
        raise ValueError(
            'One of `yaml_file` or `yaml_objects` arguments must be provided')


def delete_from_dict(k8s_client, data, verbose=False, namespace='default',
                     **kwargs):
    """
    """
    # If it is a list type, will need to iterate its items
    api_exceptions = []
    k8s_objects = []

    if "List" in data["kind"]:
        # Could be "List" or "Pod/Service/...List"
        # This is a list type. iterate within its items
        kind = data["kind"].replace("List", "")
        for yml_object in data["items"]:
            # Mitigate cases when server returns a xxxList object
            # See kubernetes-client/python#586
            if kind != "":
                yml_object["apiVersion"] = data["apiVersion"]
                yml_object["kind"] = kind
            try:
                created = delete_from_yaml_single_item(
                    k8s_client, yml_object, verbose, namespace=namespace,
                    **kwargs)
                k8s_objects.append(created)
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        # This is a single object. Call the single item method
        try:
            created = delete_from_yaml_single_item(
                k8s_client, data, verbose, namespace=namespace, **kwargs)
            k8s_objects.append(created)
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    # In case we have exceptions waiting for us, raise them
    if api_exceptions:
        raise FailToDeleteError(api_exceptions)

    return k8s_objects


def delete_from_yaml_single_item(
        k8s_client, yml_object, verbose=False, **kwargs):
    group, _, version = yml_object["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    # Only replace the last instance
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    fcn_to_call = "{0}{1}Api".format(group, version.capitalize())
    k8s_api = getattr(client, fcn_to_call)(k8s_client)
    # Replace CamelCased action_type into snake_case
    kind = yml_object["kind"]
    kind = UPPER_FOLLOWED_BY_LOWER_RE.sub(r'\1_\2', kind)
    kind = LOWER_OR_NUM_FOLLOWED_BY_UPPER_RE.sub(r'\1_\2', kind).lower()
    resp = None
    # Expect the user to create namespaced objects more often
    if hasattr(k8s_api, "create_namespaced_{0}".format(kind)):
        # Decide which namespace we are going to put the object in,
        # if any
        if "namespace" in yml_object["metadata"]:
            namespace = yml_object["metadata"]["namespace"]
            kwargs['namespace'] = namespace
        name = yml_object["metadata"]["name"]
        try:
            resp = getattr(k8s_api, "delete_namespaced_{0}".format(kind))(
                name=name, body=DEFAULT_DELETION_BODY, **kwargs)
            print(f"delete {kind} {name}")
        except Exception as e:
            print(f"delete {kind} {name} failed", e)
    else:
        kwargs.pop('namespace', None)
        try:
            resp = getattr(k8s_api, "patch_{0}".format(kind))(name, **kwargs)
            print(f"delete {kind} {name}")
        except Exception as e:
            print(f"delete {kind} {name} failed", e)
    if verbose:
        msg = "{0} deleted.".format(kind)
        if hasattr(resp, 'status'):
            msg += " status='{0}'".format(str(resp.status))
        print(msg)
    return resp


class FailToDeleteError(Exception):
    """
    An exception class for handling error if an error occurred when
    handling a yaml file.
    """

    def __init__(self, api_exceptions):
        self.api_exceptions = api_exceptions

    def __str__(self):
        msg = ""
        for api_exception in self.api_exceptions:
            msg += "Error from server ({0}): {1}".format(
                api_exception.reason, api_exception.body)
        return msg
