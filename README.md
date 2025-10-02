# PeerView - AS200132 BGP Dashboard

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/netone-nl/peerview)
[![Python](https://img.shields.io/badge/python-3.11+-green.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-3.0.0-lightgrey.svg)](https://flask.palletsprojects.com)
[![Bootstrap](https://img.shields.io/badge/bootstrap-5.3.2-purple.svg)](https://getbootstrap.com)

A modern Python/Flask + Bootstrap 5 replacement for the PHP peering dashboard, providing real-time BGP session status monitoring across multiple Internet Exchange Points (IXPs).

## Features

### Modern Architecture
- **Python Flask** web framework with async support
- **Bootstrap 5** responsive UI with mobile-first design  
- **RESTful API** endpoints for programmatic access
- **Async HTTP** calls to BIRD routers for better performance
- **Caching system** to reduce load on routers
- **Docker deployment** ready with multi-stage builds

### Dashboard Capabilities
- **Real-time BGP session monitoring** across 8+ IXPs
- **Interactive filtering** by peer name, ASN, and session status
- **Sortable columns** for easy data navigation
- **Status indicators** with time-based alerts
- **Detailed peer information** in modal dialogs
- **Auto-refresh** with smart user interaction detection
- **Mobile responsive** design for on-the-go monitoring

### IXP Support
Currently configured for:
- **AMS-IX** (Amsterdam Internet Exchange)
- **Frys-IX** (Fryslan Internet Exchange) 
- **SpeedIX** (Speed Internet Exchange)
- **NL-IX** (Netherlands Internet Exchange)
- **Loc-IX** (Location Internet Exchange)
- **InterIX** (Inter Internet Exchange)
- **LayerswitchIX** (Layerswitch Internet Exchange)  
- **FogIXP** (Fog Internet Exchange Point)

### API Endpoints
- `GET /api/peers` - All peer data in JSON format
- `GET /api/peer/<asn>` - Detailed information for specific peer
- `GET /api/summary` - Dashboard summary statistics
- `GET /api/version` - Application version and build information
- `GET /health` - Health check endpoint for monitoring

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd peerview

# Build and run with Docker Compose
docker-compose up -d

# Access dashboard at http://localhost:5000
```

### Manual Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure settings (optional, defaults provided)
cp config.yaml.example config.yaml
vim config.yaml

# Run development server
python app.py

# Access dashboard at http://localhost:5000
```

### Production Deployment

```bash
# Using Gunicorn for production
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app

# Or use the provided Docker setup with Nginx
docker-compose -f docker-compose.yml up -d
```

## Configuration

### Main Configuration (`config.yaml`)

```yaml
# Session definitions and routers
session_definition_url: 'https://raw.githubusercontent.com/poweredgenl/networkstuff/main/peering/peers_as200132.yaml'
routers:
  - '195.95.177.2'
  - '195.95.177.3'

# Warning thresholds for session state changes
warning_thresholds:
  short: 86400   # 1 day in seconds
  long: 604800   # 1 week in seconds

# Application settings
app:
  host: '0.0.0.0'
  port: 5000
  debug: false
```

### Adding New IXPs

Add new exchanges to the `ixps` section in `config.yaml`:

```yaml
ixps:
  new-ix:
    pretty_name: 'New Internet Exchange'
    ipv4_range: ['192.0.2.0', '192.0.2.255']
    ipv6_range: ['2001:db8::', '2001:db8::ffff:ffff:ffff:ffff']
```

## BIRD Integration

The dashboard connects to BIRD routers via HTTP API on ports:
- **29184** for IPv4 BGP sessions
- **29186** for IPv6 BGP sessions

Ensure your BIRD configuration includes the HTTP API:

```
# BIRD configuration snippet
protocol static http_api {
    ipv4;
    route 0.0.0.0/0 via "http://127.0.0.1:29184";
}
```

## Status Indicators

The dashboard uses color-coded status indicators:

- 🟢 **Green (Established)**: BGP session is up and working
- 🟡 **Yellow (Notice)**: Session down for < 24 hours  
- 🔵 **Blue (Warning)**: Session down for < 1 week
- 🔴 **Red (Failed)**: Session down for > 1 week

## Filtering & Search

### Available Filters
- **Peer Name**: Text search in peer descriptions
- **ASN**: Filter by Autonomous System Number
- **Per-IXP Status**: Filter by session state on each exchange
  - Established
  - Configured (session exists but not established)
  - Not Connected (session down)
  - Not Configured (no session configured)

### URL Parameters
The dashboard supports URL parameters for direct filtering:

```
# Filter by peer name
/?peername=cloudflare

# Filter by ASN  
/?asn=13335

# Filter by session status on specific IXP
/?amsix_ipv4=established&amsix_ipv6=established

# Combined filters
/?peername=google&nlix_ipv4=not_connected
```

## API Usage

### Get All Peers
```bash
curl -X GET http://localhost:5000/api/peers | jq
```

### Get Specific Peer
```bash
curl -X GET http://localhost:5000/api/peer/AS13335 | jq
```

### Get Dashboard Summary
```bash
curl -X GET http://localhost:5000/api/summary | jq
```

### Example API Response
```json
{
  "AS13335": {
    "asn": "AS13335",
    "description": "Cloudflare Inc", 
    "sessions": {
      "ipv4": {
        "amsix": [
          {
            "state": "Established",
            "since": "2024-01-15T10:30:00Z",
            "neighbor_address": "80.249.208.124",
            "neighbor_as": 13335,
            "description": "Cloudflare"
          }
        ]
      },
      "ipv6": {
        "amsix": [
          {
            "state": "Established", 
            "since": "2024-01-15T10:30:00Z",
            "neighbor_address": "2001:7f8:1::a501:3335:1",
            "neighbor_as": 13335,
            "description": "Cloudflare"
          }
        ]
      }
    }
  }
}
```

## Deployment Options

### Docker Deployment

The provided `Dockerfile` uses multi-stage builds for optimal image size and security:

```dockerfile
# Multi-stage build with security hardening
FROM python:3.11-slim as builder
# ... build stage

FROM python:3.11-slim  
# ... production stage with non-root user
```

### Docker Compose

Full stack deployment with optional components:

```yaml
services:
  peering-dashboard:
    build: .
    ports:
      - "5000:5000"
      
  redis:          # Optional caching
    image: redis:7-alpine
    
  nginx:          # Optional reverse proxy
    image: nginx:alpine
    ports:
      - "80:80"
```

### systemd Service

For traditional server deployments:

```ini
[Unit]
Description=AS200132 Peering Dashboard
After=network.target

[Service]
Type=simple
User=peering-dashboard
WorkingDirectory=/opt/peering-dashboard
ExecStart=/opt/peering-dashboard/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Monitoring & Observability

### Health Checks
- **HTTP Health Check**: `GET /api/summary`
- **Docker Health Check**: Built into container
- **Kubernetes Ready**: Health check endpoints available

### Logging
Application logs are structured and include:
- HTTP request logs
- BGP session fetch errors  
- Cache hit/miss statistics
- Performance metrics

### Metrics
The application exposes metrics suitable for monitoring:
- Session counts by status and IXP
- API response times
- Cache efficiency
- Error rates

## Security Considerations

### Built-in Protections
- **Input validation** on all user inputs
- **SQL injection prevention** (no SQL database used)
- **XSS protection** via template escaping
- **Rate limiting** capabilities
- **Non-root container** execution

### Network Security
- Dashboard connects outbound to BIRD routers only
- No inbound connections to BIRD required
- API endpoints can be rate-limited via reverse proxy
- HTTPS termination at load balancer/proxy level

## Performance Optimization

### Caching Strategy
- **In-memory caching** of BGP session data (60s TTL default)
- **Async HTTP requests** to multiple routers in parallel
- **Connection pooling** for reduced latency
- **Conditional requests** to avoid unnecessary data transfer

### Scaling Considerations
- **Horizontal scaling**: Multiple app instances behind load balancer
- **Database caching**: Optional Redis integration
- **CDN integration**: Static assets via CDN
- **Regional deployment**: Deploy close to BIRD routers

## Troubleshooting

### Common Issues

**Dashboard shows no peers:**
```bash
# Check BIRD router connectivity
curl -v http://195.95.177.2:29184/protocols/bgp

# Check session definition URL
curl -v https://raw.githubusercontent.com/poweredgenl/networkstuff/main/peering/peers_as200132.yaml

# Check application logs
docker logs as200132-peerview
```

**Sessions show as unknown status:**
```bash
# Verify BIRD socket permissions
ls -la /run/bird/bird.ctl

# Check birdc command
birdc show protocols

# Verify IP range configuration in config.yaml
```

**Performance issues:**
```bash
# Monitor cache hit rates
grep "cache" /var/log/peerview/app.log

# Check concurrent connections to routers
netstat -an | grep "29184\|29186"

# Monitor memory usage
docker stats as200132-peerview
```

### Debug Mode

Enable debug mode for development:

```yaml
# config.yaml
app:
  debug: true
  
logging:
  level: 'DEBUG'
```

Or via environment variable:
```bash
FLASK_ENV=development python app.py
```

## Migration from PHP Version

### Key Improvements Over PHP Version
1. **Performance**: Async HTTP requests vs sequential
2. **User Experience**: Modern responsive UI vs static table
3. **API Access**: RESTful endpoints vs screen scraping
4. **Maintainability**: Clean Python code vs complex PHP
5. **Deployment**: Docker containers vs manual PHP setup
6. **Monitoring**: Structured logging and metrics
7. **Security**: Modern security practices built-in

### Migration Steps
1. **Deploy new version** alongside existing PHP
2. **Verify data accuracy** by comparing outputs
3. **Update monitoring** to use new API endpoints
4. **Switch DNS/proxy** to new application
5. **Decommission PHP version** after verification

### Data Compatibility
The new dashboard is designed to be compatible with existing:
- BIRD router configurations
- YAML session definitions
- IXP IP range mappings
- Status interpretation logic

## Contributing

### Development Setup
```bash
# Clone repository
git clone <repository-url>
cd peering-dashboard

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black app.py
flake8 app.py
```

### Adding Features
1. **New IXPs**: Add to config.yaml and update templates
2. **Additional APIs**: Follow existing patterns in app.py
3. **UI Enhancements**: Modify templates with Bootstrap 5
4. **Integrations**: Add new data sources following async patterns

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- **Issues**: Create GitHub issue for bugs/features
- **Documentation**: Check this README and inline code comments
- **Community**: NetOne.nl NOC team

---

**PeerView v1.0.0** - Modern BGP peering dashboard for AS200132, built with Python, Flask, and Bootstrap 5.