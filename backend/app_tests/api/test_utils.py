import pytest
import json
import re
from django.db.models.fields.related_descriptors import ManyToManyDescriptor
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from ciso_assistant.settings import EMAIL_HOST, EMAIL_HOST_RESCUE

from test_vars import *


class EndpointTestsUtils:
    """Provides utils functions for API endpoints testing"""

    def get_endpoint_url(verbose_name: str, resolved: bool = True):
        """Get the endpoint URL for the given object"""

        endpoint_varname = format_endpoint(verbose_name)
        endpoint = get_var(endpoint_varname)
        return reverse(endpoint) if resolved else endpoint

    def get_object_urn(object_name: str, resolved: bool = True):
        """Get the object URN for the given object"""

        urn_varname = format_urn(object_name)
        urn = get_var(urn_varname)
        return f"{reverse(LIBRARIES_ENDPOINT)}{urn}/" if resolved else eval(urn)

    @pytest.mark.django_db
    def get_test_client_and_folder(authenticated_client, role: str, test_folder_name: str, assigned_folder_name: str = "test"):
        """Get an authenticated client with a specific role and the folder associated to the role"""
        from iam.models import Folder, User, UserGroup

        EndpointTestsQueries.Auth.create_object(
            authenticated_client, "Folders", Folder, {"name": assigned_folder_name},
            item_search_field="name"
        )
        assigned_folder = test_folder = Folder.objects.get(name=assigned_folder_name)

        if test_folder_name != assigned_folder_name:
            EndpointTestsQueries.Auth.create_object(
                authenticated_client, "Folders", Folder, {"name": test_folder_name}, base_count=1,
                item_search_field="name"
            )
            test_folder = Folder.objects.get(name=test_folder_name)

        user = User.objects.create_user(TEST_USER_EMAIL)
        UserGroup.objects.get(
            name=role,
            folder=Folder.objects.get(name=GROUPS_PERMISSIONS[role]["folder"]),
        ).user_set.add(user)
        client = APIClient()
        client.force_login(user)
        return client, test_folder, assigned_folder

    def expected_request_response(
        action: str, object: str, scope: str, user_group: str, expected_status: int = status.HTTP_200_OK
    ):
        """Get the expected request response for a specific action on an object for a specific user group"""
        perm_name = f"{action}_{get_singular_name(object).lower().replace(' ', '')}"

        if perm_name in GROUPS_PERMISSIONS[user_group]["perms"]:
            # User has permission to perform the action
            if (GROUPS_PERMISSIONS[user_group]["folder"] == "Global") or (scope == GROUPS_PERMISSIONS[user_group]["folder"]) or (scope == "Global"):
                # User has access to the domain
                return False, expected_status, "ok"
            else:
                return False, expected_status, "outside_scope"
        else:
            # User has not permission to perform the action
            if (GROUPS_PERMISSIONS[user_group]["folder"] == "Global") or (scope == GROUPS_PERMISSIONS[user_group]["folder"]) or (scope == "Global"):
                # User has access to the domain
                return True, status.HTTP_403_FORBIDDEN, "permission_denied"
            else:
                return True, status.HTTP_403_FORBIDDEN, "outside_scope"


class EndpointTestsQueries:
    """Provides tests functions for API endpoints testing"""

    def get_object(
        client,
        verbose_name: str,
        object=None,
        build_params: dict = None,
        endpoint: str = None,
    ):
        """Test to get object from the API without authentication

        :param client: the client (not authenticated) to use for the test
        :param verbose_name: the verbose name of the object to test
        :param object: the object to test (optional)
        :param build_params: the parameters to build the object (optional)
        :param endpoint: the endpoint URL of the object to test (optional)
        """

        url = endpoint or EndpointTestsUtils.get_endpoint_url(verbose_name)

        # Uses the API endpoint to assert that objects are not accessible
        response = client.get(url)

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} are accessible without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} are accessible without authentication"

        # Creates a test object from the model
        if build_params and object:
            if object.__name__ == "User":
                object.objects.create_user(
                    **build_params
                )  # a password is required in the build_params
            else:
                m2m_fields = {}
                non_m2m_fields = {}

                for field, value in build_params.items():
                    if isinstance(getattr(object, field, None), ManyToManyDescriptor):
                        m2m_fields[field] = value
                    else:
                        non_m2m_fields[field] = value

                # Create the object without many-to-many fields
                test_object = object.objects.create(**non_m2m_fields)

                # Now, set the many-to-many fields
                for field, value in m2m_fields.items():
                    getattr(test_object, field).set(value)
        # Uses the API endpoint to assert that the test object is not accessible
        response = client.get(url)

        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} are accessible without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} are accessible without authentication"

    def create_object(
        client, verbose_name: str, object, test_params: dict, endpoint: str = None
    ):
        """Test to create object with the API without authentication

        :param client: the client (not authenticated) to use for the test
        :param verbose_name: the verbose name of the object to test
        :param object: the object to test
        :param test_params: the parameters of the object to test (optional)
        :param endpoint: the endpoint URL of the object to test (optional)
        """

        url = endpoint or EndpointTestsUtils.get_endpoint_url(verbose_name)
        count = object.objects.all().count()

        # Uses the API endpoint to create an object without authentication
        response = client.post(url, test_params, format="json")

        # Asserts that the user was not created
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} can be created without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} can be created without authentication"

        # Checks that the object was not created in the database
        assert (
            count == object.objects.all().count()
        ), f"{verbose_name} created with the API without authentication are still saved in the database"

    def update_object(
        client,
        verbose_name: str,
        object,
        build_params: dict,
        update_params: dict,
        endpoint: str = None,
    ):
        """Test to update object with the API without authentication

        :param client: the client (not authenticated) to use for the test
        :param verbose_name: the verbose name of the object to test
        :param object: the object to test
        :param build_params: the parameters of the object to test
        :param update_params: the parameters to update the object
        :param endpoint: the endpoint URL of the object to test (optional)
        """

        m2m_fields = {}
        non_m2m_fields = {}

        for field, value in build_params.items():
            if isinstance(getattr(object, field, None), ManyToManyDescriptor):
                m2m_fields[field] = value
            else:
                non_m2m_fields[field] = value

        # Create the object without many-to-many fields
        test_object = object.objects.create(**non_m2m_fields)

        # Now, set the many-to-many fields
        for field, value in m2m_fields.items():
            getattr(test_object, field).set(value)

        url = endpoint or (
            EndpointTestsUtils.get_endpoint_url(verbose_name)
            + str(test_object.id)
            + "/"
        )

        # Uses the API endpoint to update an object without authentication
        response = client.patch(url, update_params, format="json")

        # Asserts that the user was not updated
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} can be updated without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} can be updated without authentication"

        # Checks that the object was not updated in the database
        field = list(update_params.items())[0]
        assert (
            build_params[field[0]] == getattr(test_object, field[0]) != field[1]
        ), f"{verbose_name} updated with the API without authentication are still saved in the database"

    def delete_object(
        client, verbose_name: str, object, build_params: dict = {}, endpoint: str = None
    ):
        """Test to delete object with the API without authentication

        :param client: the client (not authenticated) to use for the test
        :param verbose_name: the verbose name of the object to test
        :param object: the object to test
        :param build_params: the parameters of the object to test
        :param endpoint: the endpoint URL of the object to test (optional)
        """

        if build_params:
            # Creates a test object from the model
            m2m_fields = {}
            non_m2m_fields = {}

            for field, value in build_params.items():
                if isinstance(getattr(object, field, None), ManyToManyDescriptor):
                    m2m_fields[field] = value
                else:
                    non_m2m_fields[field] = value

            # Create the object without many-to-many fields
            test_object = object.objects.create(**non_m2m_fields)

            # Now, set the many-to-many fields
            for field, value in m2m_fields.items():
                getattr(test_object, field).set(value)
            id = str(test_object.id)
        else:
            id = str(object.objects.all()[0].id)

        url = endpoint or (EndpointTestsUtils.get_endpoint_url(verbose_name) + id + "/")

        # Uses the API endpoint to delete an object without authentication
        response = client.delete(url)

        # Asserts that the user was not deleted
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} can be deleted without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} can be deleted without authentication"

        # Checks that the object was not deleted in the database
        assert object.objects.filter(
            id=id
        ).exists(), f"{verbose_name} deleted with the API without authentication are not saved in the database"

    def import_object(client, verbose_name: str, urn: str = None):
        """Imports object with the API without authentication

        :param client: the client (not authenticated) to use for the test
        :param verbose_name: the verbose name of the object to test
        :param urn: the endpoint URL of the object to test (optional)
        """

        url = urn or EndpointTestsUtils.get_object_urn(verbose_name)

        # Uses the API endpoint to import an object without authentication
        response = client.get(url + "import/")

        # Asserts that the object was imported successfully
        assert (
            response.status_code == status.HTTP_403_FORBIDDEN
        ), f"{verbose_name} can be imported without authentication"
        assert response.json() == {
            "detail": "Authentication credentials were not provided."
        }, f"{verbose_name} can be imported without authentication"

    class Auth:
        """Provides authenticated tests functions for API endpoints testing"""

        def get_object(
            authenticated_client,
            verbose_name: str,
            object=None,
            build_params: dict = {},
            test_params: dict = {},
            base_count: int = 0,
            item_search_field: str = None,
            endpoint: str = None,
            fails: bool = False,
            expected_status: int = status.HTTP_200_OK,
            user_group: str = None,
            scope: str = None,
        ):
            """Test to get object from the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param object: the object to test (optional)
            :param build_params: the parameters to build the object (optional). The objects used to build the object should be provided as instances of the object model
            :param test_params: the parameters of the object to test in addition to the build params (optional)
            :param base_count: the number of objects in the database before the test (optional)
                -1 means that the number of objects is unknown
            :param endpoint: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status, user_perm_reason = None, 0, None

            if user_group:
                scope = scope or str(build_params.get("folder", None)) # if the scope is not provided, try to get it from the build_params
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    user_perm_reason
                ) = EndpointTestsUtils.expected_request_response(
                    "view", verbose_name, scope, user_group, expected_status
                )

            url = endpoint or EndpointTestsUtils.get_endpoint_url(verbose_name)

            # Uses the API endpoint to assert that objects are accessible
            response = authenticated_client.get(url)

            if not user_group or user_perm_expected_status == status.HTTP_200_OK:
                # User has permission to view the object
                assert response.status_code == expected_status, (
                    f"{verbose_name} are not accessible with permission"
                    if expected_status == status.HTTP_200_OK
                    else f"{verbose_name} should not be accessible (expected status: {expected_status})"
                )
            else:
                # User does not have permission to view the object
                assert response.status_code == user_perm_expected_status, (
                    f"{verbose_name} are accessible without permission"
                    if response.status_code == status.HTTP_200_OK
                    else f"Accessing {verbose_name.lower()} should give a status {user_perm_expected_status}"
                )

            if not (fails or user_perm_fails):
                if not (object and build_params) and test_params:
                    if base_count == 0:
                        # perfom a test with an externally created object
                        assert (
                            response.json()["count"] == base_count + 1
                        ), f"{verbose_name} are not accessible with authentication"
                    elif base_count < 0:
                        assert (
                            len(response.json()["results"]) != 0
                        ), f"{verbose_name} are not accessible with authentication"
                elif base_count > 0:
                    assert (
                        response.json()["count"] == base_count
                    ), f"{verbose_name} are not accessible with authentication"

            # Creates a test object from the model
            if build_params and object:
                if object.__name__ == "User":
                    object.objects.create_superuser(
                        **build_params
                    )  # no password is required in the build_params
                else:
                    m2m_fields = {}
                    non_m2m_fields = {}

                    for field, value in build_params.items():
                        if isinstance(
                            getattr(object, field, None), ManyToManyDescriptor
                        ):
                            m2m_fields[field] = value
                        else:
                            non_m2m_fields[field] = value

                    # Create the object without many-to-many fields
                    test_object = object.objects.create(**non_m2m_fields)

                    # Now, set the many-to-many fields
                    for field, value in m2m_fields.items():
                        getattr(test_object, field).set(value)

                # Uses the API endpoint to assert that the test object is accessible
                response = authenticated_client.get(url)

                if not user_group or user_perm_expected_status == status.HTTP_200_OK:
                    # User has permission to view the object
                    assert response.status_code == expected_status, (
                        f"{verbose_name} are not accessible with permission"
                        if expected_status == status.HTTP_200_OK
                        else f"{verbose_name} should not be accessible (expected status: {expected_status})"
                    )
                else:
                    # User does not have permission to view the object
                    assert response.status_code == user_perm_expected_status, (
                        f"{verbose_name} are accessible without permission"
                        if response.status_code == status.HTTP_200_OK
                        else f"Accessing {verbose_name.lower()} should give a status {user_perm_expected_status}"
                    )

                if not (fails or user_perm_fails):
                    if user_perm_reason == "outside_scope":
                        if not base_count < 0:
                            assert (
                                response.json()["count"] == 0
                            ), f"{verbose_name} are accessible outside the domain"
                    else:
                        if base_count < 0:
                            assert (
                                len(response.json()["results"]) != 0
                            ), f"{verbose_name} are not accessible with authentication"
                        else:
                            assert (
                                response.json()["count"] == base_count + 1
                            ), f"{verbose_name} are not accessible with authentication"

            if not (fails or user_perm_fails) and user_perm_reason != "outside_scope" and len(response.json()["results"]) != 0:
                params = {**build_params, **test_params}
                if len(response.json()["results"]) > 0 and item_search_field:
                    response_item = [
                        res
                        for res in response.json()["results"]
                        if res[item_search_field] == params[item_search_field]
                    ][0]
                else:
                    response_item = response.json()["results"][-1]
                for key, value in params.items():
                    if type(value) == dict and type(response_item[key]) == str:
                        assert (
                            json.loads(response_item[key]) == value
                        ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"
                    else:
                        assert (
                            response_item[key] == value
                        ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"

        def get_object_options(
            authenticated_client,
            verbose_name: str,
            option: str,
            choices: list,
            endpoint: str = None,
            fails: bool = False,
            expected_status: int = status.HTTP_200_OK,
            user_group: str = None,
            scope: str = None,
        ):
            """Test to get object options from the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param object: the object to test
            :param option: the option to test
            :param endpoint: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status = None, 0

            if user_group and not fails:
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    _
                ) = EndpointTestsUtils.expected_request_response(
                    "view", verbose_name, scope, user_group, expected_status
                )

            url = endpoint or EndpointTestsUtils.get_endpoint_url(verbose_name)

            # Uses the API endpoint to assert that the object options are accessible
            response = authenticated_client.get(url + option + "/")

            if not user_group or user_perm_expected_status == status.HTTP_200_OK:
                # User has permission to view the object
                assert response.status_code == expected_status, (
                    f"{verbose_name} {option} choices are not accessible with permission"
                    if expected_status == status.HTTP_200_OK
                    else f"{verbose_name} {option} should not be accessible (expected status: {expected_status})"
                )
            else:
                # User does not have permission to view the object
                assert response.status_code == user_perm_expected_status, (
                    f"{verbose_name} {option} choices are accessible without permission"
                    if response.status_code == status.HTTP_200_OK
                    else f"Accessing {verbose_name.lower()} {option} should give a status {user_perm_expected_status}"
                )

            if not (fails or user_perm_fails):
                for choice in choices:
                    assert (
                        choice[0] in response.json()
                    ), f"{verbose_name} {choice} choice is not accessible from the API"
                    assert (
                        str(choice[1]) in response.json()[choice[0]]
                    ), f"{verbose_name} {choice} choice is not associated to the value {choice[1]} in the API"

        def create_object(
            authenticated_client,
            verbose_name: str,
            object,
            build_params: dict,
            test_params: dict = {},
            base_count: int = 0,
            item_search_field: str = None,
            endpoint: str | None = None,
            query_format: str = "json",
            fails: bool = False,
            expected_status: int = status.HTTP_201_CREATED,
            user_group: str = None,
            scope: str = None,
        ):
            """Test to create object with the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param build_params: the parameters to build the object. Objects references to create the object should be provided as stringified UUIDs
            :param test_params: the parameters of the object to test in addition to the build params (optional)
                the test_params can ovveride the build_params
            :param base_count: the number of objects in the database before the test (optional)
                -1 means that the number of objects is unknown
            :param endpoint: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status, user_perm_reason = None, 0, None

            if user_group:
                scope = scope or str(build_params.get("folder", None)) # if the scope is not provided, try to get it from the build_params
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    user_perm_reason
                ) = EndpointTestsUtils.expected_request_response(
                    "add", verbose_name, scope, user_group, expected_status
                )

            url = endpoint or EndpointTestsUtils.get_endpoint_url(verbose_name)

            # Uses the API endpoint to create an object with authentication
            response = authenticated_client.post(url, build_params, format=query_format)

            if fails:
                # Asserts that the object was not created
                assert (
                    response.status_code == expected_status
                ), f"{verbose_name} can not be created with authentication"
                return

            # Asserts that the object was created successfully
            if not user_group or user_perm_expected_status == status.HTTP_201_CREATED:
                if user_perm_reason == "outside_scope":
                    assert response.status_code == status.HTTP_403_FORBIDDEN, (
                        f"{verbose_name} can be created outside the domain"
                        if response.status_code == status.HTTP_201_CREATED
                        else f"Creating {verbose_name.lower()} should give a status {status.HTTP_403_FORBIDDEN}"
                    )
                else:
                    # User has permission to create the object
                    assert response.status_code == expected_status, (
                        f"{verbose_name} can not be created with authentication"
                        if expected_status == status.HTTP_201_CREATED
                        else f"{verbose_name} should not be created (expected status: {expected_status})"
                    )
            else:
                # User does not have permission to create the object
                assert response.status_code == user_perm_expected_status, (
                    f"{verbose_name} can be created without permission"
                    if response.status_code == status.HTTP_201_CREATED
                    else f"Creating {verbose_name.lower()} should give a status {user_perm_expected_status}"
                )

            if not (fails or user_perm_fails):
                if user_perm_reason == "outside_scope":
                    assert (
                        response.json()['folder'] == 'You do not have permission to create objects in this folder'
                        ), f"{verbose_name} can be created outside the domain"
                else:
                    for key, value in build_params.items():
                        if key == "attachment":
                            # Asserts that the value file name is present in the JSON response
                            assert (
                                value.name.split("/")[-1].split(".")[0]
                                in response.json()[key]
                            ), f"{verbose_name} {key.replace('_', ' ')} returned by the API after object creation don't match the provided {key.replace('_', ' ')}"
                        else:
                            assert (
                                response.json()[key] == value
                            ), f"{verbose_name} {key.replace('_', ' ')} returned by the API after object creation don't match the provided {key.replace('_', ' ')}"

                    # Checks that the object was created in the database
                    assert (
                        object.objects.filter(id=response.json()["id"]).exists()
                    ), f"{verbose_name} created with the API are not saved in the database"

            # Uses the API endpoint to assert that the created object is accessible
            response = authenticated_client.get(url)

            assert (
                response.status_code == status.HTTP_200_OK
            ), f"{verbose_name} are not accessible with authentication"

            if not (fails or user_perm_fails) and len(response.json()["results"]) != 0:
                params = {**build_params, **test_params}
                if response.json()["count"] > 0 and item_search_field:
                    response_item = [
                        res
                        for res in response.json()["results"]
                        if res[item_search_field] == params[item_search_field]
                    ][0]
                else:
                    response_item = response.json()["results"][base_count]
                for key, value in params.items():
                    if key == "attachment" and response_item[key] != value:
                        # Asserts that the value file name is present in the JSON response
                        assert (
                            re.sub(
                                r"_([a-z]|[A-Z]|[0-9]){7}(?:\.)",
                                ".",
                                response_item[key],
                            )
                            == value
                        ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"
                    else:
                        assert (
                            response_item[key] == value
                        ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"

        def update_object(
            authenticated_client,
            verbose_name: str,
            object,
            build_params: dict,
            update_params: dict,
            test_build_params: dict = {},
            test_params: dict = {},
            endpoint: str | None = None,
            query_format: str = "json",
            fails: bool = False,
            expected_status: int = status.HTTP_200_OK,
            user_group: str = None,
            scope: str = None,
        ):
            """Test to update object with the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param build_params: the parameters to build the object. The objects used to build the object should be provided as instances of the object model
            :param update_params: the parameters to update the object. Objects references to update the object should be provided as stringified UUIDs
            :param test_params: the parameters of the modified object to test (optional)
                the test_params can ovveride the build_params
            :param endpoint: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status, user_perm_reason = None, 0, None

            if user_group:
                scope = scope or str(build_params.get("folder", None)) # if the scope is not provided, try to get it from the build_params
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    user_perm_reason
                ) = EndpointTestsUtils.expected_request_response(
                    "change", verbose_name, scope, user_group, expected_status
                )

            # Creates a test object from the model
            m2m_fields = {}
            non_m2m_fields = {}

            for field, value in build_params.items():
                if isinstance(getattr(object, field, None), ManyToManyDescriptor):
                    m2m_fields[field] = value
                else:
                    non_m2m_fields[field] = value

            # Create the object without many-to-many fields
            test_object = object.objects.create(**non_m2m_fields)
            id = str(test_object.id)

            # Now, set the many-to-many fields
            for field, value in m2m_fields.items():
                getattr(test_object, field).set(value)

            url = endpoint or (
                EndpointTestsUtils.get_endpoint_url(verbose_name)
                + str(test_object.id)
                + "/"
            )

            response = authenticated_client.get(url)

            view_perms = EndpointTestsUtils.expected_request_response("view", verbose_name, scope, user_group)
            if not user_group or view_perms[:2] == (False, status.HTTP_200_OK):
                if view_perms[2] == "outside_scope":
                    assert (
                        response.status_code == status.HTTP_404_NOT_FOUND
                    ), f"{verbose_name} object detail can be accessed outside the domain"
                else:
                    if (verbose_name is not "Users"): # Users don't have permission to view users details
                        assert (
                            response.status_code == status.HTTP_200_OK
                        ), f"{verbose_name} object detail can not be accessed with permission"
            else:
                assert (
                    response.status_code == status.HTTP_403_FORBIDDEN
                ), f"{verbose_name} object detail can be accessed without permission"

            if not (fails or user_perm_fails):
                if view_perms[2] == "outside_scope":
                    assert (
                        response.json() == {'detail': 'Not found.'}
                    ), f"{verbose_name} object detail can be accessed outside the domain"
                else:
                    for key, value in {**build_params, **test_build_params}.items():
                        if key == "attachment":
                            # Asserts that the value file name is present in the JSON response
                            assert (
                                value.name.split("/")[-1].split(".")[0]
                                in response.json()[key]
                            ), f"{verbose_name} {key.replace('_', ' ')} returned by the API after object creation don't match the provided {key.replace('_', ' ')}"
                        else:
                            assert (
                                response.json()[key] == value
                            ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"

            update_response = authenticated_client.patch(
                url, update_params, format=query_format
            )

            if user_perm_reason == "outside_scope":
                assert (
                    update_response.status_code == status.HTTP_404_NOT_FOUND
                ), f"{verbose_name} can be accessed outside the domain"
            else:
                if not user_group or user_perm_expected_status == status.HTTP_200_OK:
                    # User has permission to update the object
                    assert update_response.status_code == expected_status, (
                        f"{verbose_name} can not be updated with authentication"
                        if expected_status == status.HTTP_200_OK
                        else f"{verbose_name} should not be updated (expected status: {expected_status})"
                    )
                else:
                    # User does not have permission to update the object
                    assert update_response.status_code == user_perm_expected_status, (
                        f"{verbose_name} can be updated without permission"
                        if update_response.status_code == status.HTTP_200_OK
                        else f"Updating {verbose_name.lower()} should give a status {user_perm_expected_status}"
                    )

                if not (fails or user_perm_fails):
                    for key, value in {
                        **build_params,
                        **update_params,
                        **test_params,
                    }.items():
                        if key == "attachment" and update_response.json()[key] != value:
                            # Asserts that the value file name is present in the JSON response
                            assert (
                                value.split("/")[-1].split(".")[0]
                                in update_response.json()[key]
                            ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"
                        else:
                            assert (
                                update_response.json()[key] == value
                            ), f"{verbose_name} {key.replace('_', ' ')} queried from the API don't match {verbose_name.lower()} {key.replace('_', ' ')} in the database"

        def delete_object(
            authenticated_client,
            verbose_name: str,
            object,
            build_params: dict = {},
            endpoint: str = None,
            fails: bool = False,
            expected_status: int = status.HTTP_204_NO_CONTENT,
            user_group: str = None,
            scope: str = None,
        ):
            """Test to delete object with the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param build_params: the parameters to build the object. The objects used to build the object should be provided as instances of the object model
            :param endpoint: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status, user_perm_reason = None, 0, None

            if user_group:
                scope = scope or str(build_params.get("folder", None)) # if the scope is not provided, try to get it from the build_params
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    user_perm_reason
                ) = EndpointTestsUtils.expected_request_response(
                    "delete", verbose_name, scope, user_group, expected_status
                )

            if build_params:
                # Creates a test object from the model
                m2m_fields = {}
                non_m2m_fields = {}

                for field, value in build_params.items():
                    if isinstance(getattr(object, field, None), ManyToManyDescriptor):
                        m2m_fields[field] = value
                    else:
                        non_m2m_fields[field] = value

                # Create the object without many-to-many fields
                test_object = object.objects.create(**non_m2m_fields)
                id = str(test_object.id)

                # Now, set the many-to-many fields
                for field, value in m2m_fields.items():
                    getattr(test_object, field).set(value)
            else:
                id = str(object.objects.all()[0].id)

            url = endpoint or (
                EndpointTestsUtils.get_endpoint_url(verbose_name) + id + "/"
            )

            # Asserts that the objects exists
            response = authenticated_client.get(url)

            view_perms = EndpointTestsUtils.expected_request_response("view", verbose_name, scope, user_group)
            if not user_group or view_perms[:2] == (False, status.HTTP_200_OK):
                if view_perms[2] == "outside_scope":
                    assert (
                        response.status_code == status.HTTP_404_NOT_FOUND
                    ), f"{verbose_name} object detail can be accessed outside the domain"
                else:
                    if (verbose_name is not "Users"): # Users don't have permission to view users details
                        assert (
                            response.status_code == status.HTTP_200_OK
                        ), f"{verbose_name} object detail can not be accessed with permission"
            else:
                assert (
                    response.status_code == status.HTTP_403_FORBIDDEN
                ), f"{verbose_name} object detail can be accessed without permission"

            # Asserts that the object was deleted successfully
            delete_response = authenticated_client.delete(url)

            if user_perm_reason == "outside_scope":
                assert (
                    delete_response.status_code == status.HTTP_404_NOT_FOUND
                ), f"{verbose_name} can be accessed outside the domain"
            else:
                if (
                    not user_group
                    or user_perm_expected_status == status.HTTP_204_NO_CONTENT
                ):
                    # User has permission to delete the object
                    assert delete_response.status_code == expected_status, (
                        f"{verbose_name} can not be deleted with permission"
                        if expected_status == status.HTTP_204_NO_CONTENT
                        else f"{verbose_name} should not be deleted (expected status: {expected_status})"
                    )
                else:
                    # User does not have permission to delete the object
                    assert delete_response.status_code == user_perm_expected_status, (
                        f"{verbose_name} can be deleted without permission"
                        if delete_response.status_code == status.HTTP_204_NO_CONTENT
                        else f"Deleting {verbose_name.lower()} should give a status {user_perm_expected_status}"
                    )

                if not (fails or user_perm_fails):
                    # Asserts that the objects does not exists anymore
                    response = authenticated_client.get(url)
                    assert (
                        response.status_code == status.HTTP_404_NOT_FOUND
                    ), f"{verbose_name} has not been properly deleted with authentication"

        def import_object(
            authenticated_client,
            verbose_name: str,
            urn: str | None = None,
            fails: bool = False,
            expected_status: int = status.HTTP_200_OK,
            user_group: str = None,
            scope: str = "Global",
        ):
            """Imports object with the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param verbose_name: the verbose name of the object to test
            :param urn: the endpoint URL of the object to test (optional)
            """
            user_perm_fails, user_perm_expected_status, user_perm_reason = None, 0, None

            if user_group:
                (
                    user_perm_fails,
                    user_perm_expected_status,
                    user_perm_reason
                ) = EndpointTestsUtils.expected_request_response(
                    "add", "library", scope, user_group, expected_status
                )

            url = urn or EndpointTestsUtils.get_object_urn(verbose_name)

            # Uses the API endpoint to import an object with authentication
            response = authenticated_client.get(url + "import/")

            # Asserts that the object was imported successfully
            if not user_group or user_perm_expected_status == status.HTTP_200_OK:
                # User has permission to import the library
                assert response.status_code == expected_status, (
                    f"{verbose_name} can not be imported with authentication"
                    if expected_status == status.HTTP_200_OK
                    else f"{verbose_name} should not be imported (expected status: {expected_status})"
                )
            else:
                # User does not have permission to import the library
                assert response.status_code == user_perm_expected_status, (
                    f"{verbose_name} can be imported without permission"
                    if response.status_code == status.HTTP_200_OK
                    else f"Importing {verbose_name.lower()} should give a status {user_perm_expected_status}"
                )

            if not (fails or user_perm_fails):
                assert response.json() == {
                    "status": "success"
                }, f"{verbose_name} can not be imported with authentication"

        def compare_results(
            authenticated_client,
            object_name: str,
            compare_url: str,
            reference_url: str,
            test_params: list,
            count: int = 5,
            fails: bool = False,
            expected_status: int = status.HTTP_200_OK,
        ):
            """Test to compare 2 endpoints results from the API with authentication

            :param authenticated_client: the client (authenticated) to use for the test
            :param object_name: the name of the object to compare
            :param compare_url: the endpoint URL of the endpoint to compare
            :param reference_url: the endpoint URL of the reference endpoint to compare to
            :param test_params: the parameters to test
                params can be a tuple with the parameter name and the expected value or a string with the parameter name
            :param count: the number of objects to tests for each endpoint - default is 5
            """

            # Uses the API endpoints to get the reference objects list
            reference = authenticated_client.get(reference_url)
            assert (
                reference.status_code == status.HTTP_200_OK
            ), f"reference endpoint is not accessible"

            for object in reference.json()["objects"]["framework"][
                object_name.lower().replace(" ", "_")
            ][:count]:
                comparelist = authenticated_client.get(compare_url)
                compare = dict()
                assert (
                    comparelist.status_code == expected_status
                ), f"{object['name']} is not in {compare_url} results"

                # find the object in the objects list
                if not fails:
                    for c in comparelist.json()["results"]:
                        if c["urn"] == object["urn"]:
                            compare = c

                # assert that the values are the same for the given parameters
                for param in test_params:
                    if param in object and param in compare:
                        if type(param) == tuple:
                            assert (
                                object[param[0]] == param[1]
                            ), f"the reference {param[0]} value is not {param[1]}"
                            assert (
                                compare[param[0]] == param[1]
                            ), f"the endpoint to compare {param[0]} value is not {param[1]}"
                        else:
                            assert (
                                compare[param] == object[param]
                            ), f"the endpoint to compare {param[0]} value is not {param[1]}"
