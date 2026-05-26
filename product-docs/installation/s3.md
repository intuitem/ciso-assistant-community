---
description: How to connect your S3 block storage for your installation
---

# Setting up S3

By default, CISO Assistant stores attachments on the local filesystem.\
You can configure it to use an S3-compatible object storage (AWS S3, MinIO, etc.).

### Prerequisitories

* A running S3-compatible storage
* An existing bucket (must be created **before** starting CISO Assistant)
* Valid access credentials (Access Key / Secret Key)

### Configure environment variables&#x20;

Set the following environment variables in the backend environment:

```
export USE_S3=True
export AWS_ACCESS_KEY_ID=<your-access-key>
export AWS_SECRET_ACCESS_KEY=<your-secret-key>
export AWS_STORAGE_BUCKET_NAME=<your-bucket-name>
export AWS_S3_ENDPOINT_URL=<your-s3-endpoint>
```

That's it ! You can now launch your backend and your attachments will be sent to your S3 🔥

### Example case : local MinIO block storage&#x20;

You can test S3 support using MinIO:

```
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=ciso-assistant-admin \
  -e MINIO_ROOT_PASSWORD=not_secure_password \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"
```

Then go on [http://localhost:9001](http://localhost:9001) , enter your minio root user/password and create a bucket with the name 'my-ciso-bucket'.

The backend environment variables will be:

```
export USE_S3=True
export AWS_ACCESS_KEY_ID=ciso-assistant-admin
export AWS_SECRET_ACCESS_KEY=not_secure_password
export AWS_STORAGE_BUCKET_NAME=my-ciso-bucket
export AWS_S3_ENDPOINT_URL=http://localhost:9000
```

You can now see your attachments on the MinIO console after importing them in ciso-assistant.
