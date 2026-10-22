"""Async-friendly collectors. Each returns [(external_id, metric, value, unit, datetime)]."""
import asyncio
import json
from datetime import datetime, timedelta, timezone

Sample = tuple  # (external_id, metric, value, unit, ts)


def _collect_aws(secret: dict, region: str) -> list[Sample]:
    import boto3
    sess = boto3.Session(aws_access_key_id=secret["access_key_id"], aws_secret_access_key=secret["secret_access_key"],
                         region_name=region)
    ec2, cw = sess.client("ec2"), sess.client("cloudwatch")
    ids = [i["InstanceId"] for r in ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])["Reservations"]
           for i in r["Instances"]]
    out, end = [], datetime.now(timezone.utc)
    for iid in ids:
        q = [{"Id": m.lower(), "MetricStat": {"Metric": {"Namespace": "AWS/EC2", "MetricName": m,
              "Dimensions": [{"Name": "InstanceId", "Value": iid}]}, "Period": 300, "Stat": "Average"}}
             for m in ("CPUUtilization", "NetworkIn", "NetworkOut")]
        res = cw.get_metric_data(MetricDataQueries=q, StartTime=end - timedelta(minutes=15), EndTime=end)
        names = {"cpuutilization": ("cpu", "%"), "networkin": ("net_in", "B"), "networkout": ("net_out", "B")}
        for r in res["MetricDataResults"]:
            metric, unit = names[r["Id"]]
            out += [(iid, metric, v, unit, t) for t, v in zip(r["Timestamps"], r["Values"])]
    return out


def _collect_gcp(secret: dict, region: str) -> list[Sample]:
    from google.cloud import monitoring_v3
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_info(secret["service_account"])
    client = monitoring_v3.MetricServiceClient(credentials=creds)
    now = datetime.now(timezone.utc)
    interval = monitoring_v3.TimeInterval(end_time=now, start_time=now - timedelta(minutes=15))
    series = client.list_time_series(request={
        "name": f"projects/{secret['service_account']['project_id']}",
        "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
        "interval": interval, "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL})
    return [(ts.resource.labels["instance_id"], "cpu", p.value.double_value * 100, "%", p.interval.end_time)
            for ts in series for p in ts.points]


def _collect_k8s(secret: dict, region: str) -> list[Sample]:
    from kubernetes import client, config
    config.load_kube_config_from_dict(json.loads(secret["kubeconfig"])) if isinstance(secret["kubeconfig"], str) \
        else config.load_kube_config_from_dict(secret["kubeconfig"])
    api, now = client.CustomObjectsApi(), datetime.now(timezone.utc)
    items = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "pods")["items"]
    out = []
    for it in items:
        pid = f"{it['metadata']['namespace']}/{it['metadata']['name']}"
        cpu = sum(int(c["usage"]["cpu"].rstrip("n") or 0) for c in it["containers"]) / 1e7  # nanocores -> % of 1 core*0.1
        out.append((pid, "cpu", cpu, "%", now))
    return out


COLLECTORS = {"aws": _collect_aws, "gcp": _collect_gcp, "k8s": _collect_k8s}


async def collect(provider: str, secret: dict, region: str) -> list[Sample]:
    return await asyncio.to_thread(COLLECTORS[provider], secret, region or "")
