# Kubernetes Failure Scenarios

Intentional failure manifests used to test the NudgeOps against real
cluster problems. Apply them to a disposable namespace, run an investigation
via the frontend or `POST /investigate`, and confirm the diagnosis matches the
expected result below. Clean up afterwards.

## Apply / cleanup

All scenarios live in the `nudgeops-test` namespace:

```bash
kubectl create namespace nudgeops-test
kubectl apply -f k8s-test-scenarios/01-crashloopbackoff.yaml
kubectl apply -f k8s-test-scenarios/02-imagepullbackoff.yaml
kubectl apply -f k8s-test-scenarios/03-oomkilled.yaml
kubectl apply -f k8s-test-scenarios/04-service-selector-mismatch.yaml
```

Wait for the failures to surface (30-90 seconds), because stuck-pending and
ContainerCreating pods are only reported after a grace period:

```bash
kubectl -n nudgeops-test get pods
kubectl -n nudgeops-test get events --sort-by=.lastTimestamp
```

Then select the cluster in the dashboard, click **Investigate Cluster**, and
compare the diagnosis with the expected results. To clean up:

```bash
kubectl delete namespace nudgeops-test
```

## Expected results

### Scenario 1 - CrashLoopBackOff (missing environment variable)

- Symptom: `nudgeops-crashloop-*` pod restarts with `CrashLoopBackOff`.
- The app exits immediately because `REQUIRED_SETTING` is not set.
- Expected diagnosis: root cause names the missing required environment
  variable; suggested fix adds the missing secret/configmap value.

### Scenario 2 - ImagePullBackOff (wrong image tag)

- Symptom: `nudgeops-imagepull-*` pod is `ImagePullBackOff`.
- The tag `busybox:no-such-tag-0.0.0` does not exist in the registry.
- Expected diagnosis: root cause names the invalid image tag; suggested fix
  updates the deployment image to an existing tag.

### Scenario 3 - OOMKilled (memory limit too small)

- Symptom: `nudgeops-oom-*` pod is `OOMKilled` (exit code 137, restarts).
- The shell holds ~100MB of memory inside an 8Mi limit.
- Expected diagnosis: root cause names the memory limit being exceeded;
  suggested fix increases memory requests/limits.

### Scenario 4 - Service selector mismatch (wrong labels)

- Symptom: `nudgeops-svc` has no endpoints while its pods are healthy.
- Service selects `app=nudgeops-svc-v1`, pods are labelled
  `app=nudgeops-svc-v2`.
- Expected diagnosis: root cause names the service selector mismatch;
  suggested fix updates the service selector.

## Automated coverage

The same four scenarios are covered without a cluster by
`backend/tests/test_ai_scenarios.py`:

```bash
cd backend
python -m pytest tests -q
```
