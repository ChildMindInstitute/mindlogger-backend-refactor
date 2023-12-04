#!/bin/sh

#/usr/bin/mc alias set myminio http://minio:9000 minioaccess miniosecret;
#/usr/bin/mc mb myminio/media;
#/usr/bin/mc policy set public myminio/media;
#exit 0;

/usr/bin/mc config host add local http://minio:9000 minioaccess miniosecret;
#/usr/bin/mc rm -r --force local/${CDN__BUCKET};
/usr/bin/mc mb -p local/${CDN__BUCKET};
/usr/bin/mc policy set download local/${CDN__BUCKET};
/usr/bin/mc policy set public local/${CDN__BUCKET};
/usr/bin/mc anonymous set upload local/${CDN__BUCKET};
/usr/bin/mc anonymous set download local/${CDN__BUCKET};
/usr/bin/mc anonymous set public local/${CDN__BUCKET};

exit 0;