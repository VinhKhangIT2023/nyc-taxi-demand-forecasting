#!/bin/bash
set -eu
mkdir -p /tmp/project-hbase-conf /data/logs
cp -a /opt/hbase/conf/. /tmp/project-hbase-conf/
if [ -f /tmp/project-hbase-conf/zoo.cfg ]; then
  mv /tmp/project-hbase-conf/zoo.cfg /tmp/project-hbase-conf/zoo.cfg.disabled
fi
cp /project-config/hbase-site.xml /tmp/project-hbase-conf/hbase-site.xml
export HBASE_CONF_DIR=/tmp/project-hbase-conf
export HBASE_LOG_DIR=/data/logs
hbase master start &
master_pid=$!
hbase thrift start &
thrift_pid=$!
stop_services() {
  trap - TERM INT
  kill -TERM "$thrift_pid" "$master_pid" 2>/dev/null || true
  wait "$master_pid" || true
  wait "$thrift_pid" || true
  exit 0
}
trap stop_services TERM INT
set +e
wait "$master_pid"
code=$?
kill -TERM "$thrift_pid" 2>/dev/null || true
wait "$thrift_pid"
exit "$code"
