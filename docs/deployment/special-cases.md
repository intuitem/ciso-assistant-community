---
description: Tips and tricks regarding specific cases
---

# Special cases



### SELINUX

If you have selinux enabled on your distro, you might want to check if it's not preventing the mount volume of the docker compose; you can try something like this:

```
chcon -Rt svirt_sandbox_file_t ./db
```

