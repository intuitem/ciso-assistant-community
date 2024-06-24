from knox.auth import AuthToken


def generate_token(user):
    _auth_token = AuthToken.objects.create(user=user)
    return _auth_token[1]
