# Task #855 - Prometheus Scrape Configuration for TradeView Services

**Completed by:** Claude Agent (pete)
**Date:** 2026-03-12
**Task:** [D2] Configure Prometheus scrape targets for TradeView services

## Summary

Verified and confirmed that Prometheus on otto.local is properly configured to scrape metrics from TradeView services. The configuration was already in place and correctly set up.

## Configuration Details

**File:** `/home/pi/monitoring/prometheus/prometheus.yml`

The following scrape jobs have been configured:

### 1. TradeView API (tradeview-api)
```yaml
- job_name: 'tradeview-api'
  static_configs:
    - targets: ['192.168.10.177:8770']
      labels:
        host: 'milo'
        service: 'tradeview-api'
  scrape_interval: 15s
  scrape_timeout: 10s
```
- **Endpoint:** `http://192.168.10.177:8770/metrics`
- **Service:** Runs on milo.local
- **Status:** DOWN (service not currently running - expected 404 from API)

### 2. TradeView ML (tradeview-ml)
```yaml
- job_name: 'tradeview-ml'
  static_configs:
    - targets: ['192.168.10.167:8766']
      labels:
        host: 'pete'
        service: 'tradeview-ml'
  scrape_interval: 15s
  scrape_timeout: 10s
```
- **Endpoint:** `http://192.168.10.167:8766/metrics`
- **Service:** Runs on pete.local
- **Status:** DOWN (service not currently running)

## Verification

**Prometheus Status:** ✓ Healthy and running
- **Prometheus Web UI:** http://otto.local:9090
- **Targets Page:** http://otto.local:9090/targets
- **Health Check:** Passed

**Target Status:**
```
curl -s http://localhost:9090/api/v1/targets
```

Both scrape jobs are configured and Prometheus is actively attempting to scrape:
- `tradeview-api` - Configured with 15s scrape interval
- `tradeview-ml` - Configured with 15s scrape interval

## Next Steps

When the TradeView services are deployed and running:
1. Ensure `/metrics` endpoints are available on:
   - `http://192.168.10.177:8770/metrics` (tradeview-api on milo)
   - `http://192.168.10.167:8766/metrics` (tradeview-ml on pete)
2. Services should expose Prometheus metrics in OpenMetrics format
3. Targets will automatically transition to "UP" status in Prometheus web UI

## Related Tasks

- **Parent Task:** #843 — [D3] Run full Ansible deployment and monitoring setup
- **Related Task:** #856 — [D2] [#843-c] Create Grafana dashboard for TradeView monitoring

## Files Modified

- None (configuration was already in place)

## Verification Commands

```bash
# Check Prometheus is healthy
curl -s http://otto.local:9090/-/healthy

# View all targets
curl -s http://otto.local:9090/api/v1/targets | head -100

# View specific TradeView targets
ssh pi@otto.local "grep -A 8 'job_name.*tradeview' /home/pi/monitoring/prometheus/prometheus.yml"

# Access Prometheus UI
open http://otto.local:9090/targets
```
