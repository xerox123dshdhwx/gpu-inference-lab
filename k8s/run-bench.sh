#!/bin/bash
# Usage: bash k8s/run-bench.sh RUN_NAME TARGET_URL [USERS] [DURATION] [TOOLS] [QUALITY] [LAYOUT]
set -e
RUN=$1; TARGET=$2
USERS=${3:-"1 2 4 8 16 32 64"}; DURATION=${4:-180}
TOOLS=${5:-on}; QUALITY=${6:-on}; LAYOUT=${7:-good}
if [[ -e "results/$RUN" ]]; then
    printf 'Results already exist at results/%s. Choose a new run name.\n' "$RUN" >&2
    exit 1
fi
kubectl delete job bench --ignore-not-found
sed -e "s|__RUN__|$RUN|" -e "s|__TARGET__|$TARGET|" -e "s|__USERS__|$USERS|" \
    -e "s|__DURATION__|$DURATION|" -e "s|__TOOLS__|$TOOLS|" \
    -e "s|__QUALITY__|$QUALITY|" -e "s|__LAYOUT__|$LAYOUT|" \
    k8s/bench-job.tmpl.yaml | kubectl apply -f -
echo "Benchmark $RUN running, this takes a while..."
until kubectl logs job/bench 2>/dev/null | grep -q DONE; do sleep 30; done
POD=$(kubectl get pods -l job-name=bench -o jsonpath='{.items[0].metadata.name}')
kubectl cp "$POD:/results/$RUN" "results/$RUN"
kubectl delete job bench
uv run python analysis/summarize.py "$RUN"
