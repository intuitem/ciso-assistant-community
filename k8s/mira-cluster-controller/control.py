from kubernetes import client, config

config.load_incluster_config()
v1 = client.CoreV1Api()
v1.list_namespaced_pod("default")  
v1Apps = client.AppsV1Api()
v1Apps = v1Apps.list_namespaced_stateful_set("default")

#https://blog.knoldus.com/how-to-create-statefulsets-workloads-using-kubernetes-python-client%EF%BF%BC/
