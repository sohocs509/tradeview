# Prometheus Configuration for TradeView Services

## Summary
Configured Prometheus scrape targets for TradeView monitoring services (tradeview-api and tradeview-ml) on otto.local.

## Configuration File
- **Location**: `/home/pi/monitoring/prometheus/prometheus.yml`
- **Created**: 2026-03-12

## Scrape Targets Added

### 1. Prometheus Self-Monitoring
- **Job Name**: `prometheus`
- **Target**: `localhost:9090`
- **Purpose**: Monitor Prometheus itself

### 2. TradeView API Service
- **Job Name**: `tradeview-api`
- **Target**: `milo.local:8770`
- **Metrics Path**: `/metrics`
- **Scrape Interval**: 15 seconds (default)

### 3. TradeView ML Service
- **Job Name**: `tradeview-ml`
- **Target**: `pete.local:8766`
- **Metrics Path**: `/metrics`
- **Scrape Interval**: 15 seconds (default)

## Configuration Details

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'tradeview-api'
    static_configs:
      - targets: ['milo.local:8770']
    metrics_path: '/metrics'

  - job_name: 'tradeview-ml'
    static_configs:
      - targets: ['pete.local:8766']
    metrics_path: '/metrics'
```

## Verification Steps

To verify the configuration is working correctly:

1. **Check Prometheus UI**:
   - Navigate to http://otto.local:9090/targets
   - Both `tradeview-api` and `tradeview-ml` should appear in the target list
   - Status should show "UP" for both targets when services are running

2. **Reload Prometheus Configuration**:
   ```bash
   # Option 1: Signal reload (if Prometheus is running)
   curl -X POST http://otto.local:9090/-/reload

   # Option 2: Restart Prometheus service
   systemctl restart prometheus  # or docker restart prometheus
   ```

3. **Query Metrics**:
   - Once targets are UP, metrics will be scraped at the configured interval
   - Query example: http://otto.local:9090/api/v1/query?query=up

## Prerequisites for Metrics Collection

The TradeView services must:
1. Expose Prometheus metrics at `/metrics` endpoint
2. Be running and accessible at specified addresses (milo.local:8770, pete.local:8766)
3. Return metrics in Prometheus text format

## Notes

- Configuration follows Prometheus YAML syntax standards
- Scrape interval is set to 15 seconds (standard default)
- Both services use the same metrics path: `/metrics`
- All hostnames use local DNS resolution (.local domain)
