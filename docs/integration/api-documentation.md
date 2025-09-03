# API usage

### Access the online documentation

{% embed url="https://ca-api-doc.pages.dev" %}



### Enable the documentation locally



Enable debug mode

```sh
export DJANGO_DEBUG=True
```



Start the backend server (make sure that dependencies are installed):

```shell
python3 manage.py runserver
```



Access the swagger documentation here:

[http://127.0.0.1:8000/api/schema/swagger/](http://127.0.0.1:8000/api/schema/swagger/)



Or redoc format here:

{% embed url="http://127.0.0.1:8000/api/schema/redoc/" %}



### Interacting with the API



* Start by creating a PAT, instructions here[generating-a-pat.md](generating-a-pat.md "mention")
* Use this token to form your Authorization header, it needs to be as follows:

`Authorization: Token <your_token>`



Then you can use with any rest client or within your application or script:



<figure><img src="../.gitbook/assets/image (38).png" alt="Example with Bruno (Postman alternative)"><figcaption><p>Example with Bruno (Postman alternative)</p></figcaption></figure>

Or with curl:\


```sh
curl --request GET \
  --url http://127.0.0.1:8000/api/assets/ \
  --header 'authorization: Token a6a120f....'
```







