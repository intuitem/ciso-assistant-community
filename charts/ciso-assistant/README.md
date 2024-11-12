## Installation 

### Pulling default values

```
helm show values . > ../custom-values.yaml
```

### Creating a dedicated namespace

```
kubectl create ns ciso-assistant
```

### Install

```
helm install my-release . -f ../custom-values.yaml -n ciso-assistant
```

### Uninstall

```
helm uninstall my-release -n ciso-assistant
```


## Upgrading

When upgrading, make sure to:
1. Backup your persistent volumes
2. Update any custom values
3. Run: helm upgrade my-release . --set global.appVersion=<new_version>
