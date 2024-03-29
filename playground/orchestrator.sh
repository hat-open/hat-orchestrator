#!/bin/sh

PLAYGROUND_PATH=$(dirname "$(realpath "$0")")
. $PLAYGROUND_PATH/env.sh

LOG_LEVEL=DEBUG
CONF_PATH=$DATA_PATH/orchestrator.yaml

cat > $CONF_PATH <<EOF
type: orchestrator
log:
    version: 1
    formatters:
        console_formatter:
            format: "[%(asctime)s %(levelname)s %(name)s] %(message)s"
    handlers:
        console_handler:
            class: logging.StreamHandler
            formatter: console_formatter
            level: DEBUG
    loggers:
        hat.monitor:
            level: $LOG_LEVEL
    root:
        level: INFO
        handlers: ['console_handler']
    disable_existing_loggers: false
components:
  - name: test
    args:
        - sh
        - "-c"
        - "sleep 5 && echo test"
    delay: 0
    revive: true
    start_delay: 0.5
    create_timeout: 2
    sigint_timeout: 5
    sigkill_timeout: 2
ui:
    host: '127.0.0.1'
    port: 23021
EOF

exec $PYTHON -m hat.orchestrator \
    --conf $CONF_PATH \
    "$@"
