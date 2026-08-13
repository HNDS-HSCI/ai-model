# Public Repository Release & Archival Protocol

## GitHub Release Instructions
```bash
# 1. Create Git Tag for Release v1.0.0
git tag -a v1.0.0 -m "HSCI v1.0.0 Official Camera-Ready Publication Release (SCG-L5 / RBF-L2 / PUB-L3)"

# 2. Push Tag to Public Remote
git push origin v1.0.0

# 3. Create Source Distribution Archives
git archive --format=tar.gz --prefix=hsci-v1.0.0/ v1.0.0 -o hsci-v1.0.0.tar.gz
git archive --format=zip --prefix=hsci-v1.0.0/ v1.0.0 -o hsci-v1.0.0.zip
```
