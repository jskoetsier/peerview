#!/usr/bin/env python3
"""
PeerView - Modern BGP Peering Dashboard for AS200132
Python Flask + Bootstrap 5 replacement for PHP peering dashboard
"""

import asyncio
import aiohttp
import yaml
import json
import ipaddress
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from flask import Flask, render_template, request, jsonify
import logging

from version import get_version, get_version_info, __version__

app = Flask(__name__)
app.config['VERSION'] = __version__
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add version info to app context
@app.context_processor
def inject_version():
    return {
        'app_version': get_version(),
        'version_info': get_version_info()
    }

@dataclass
class IXPConfig:
    name: str
    pretty_name: str
    ipv4_range: Tuple[str, str]
    ipv6_range: Tuple[str, str]

@dataclass
class BGPSession:
    state: str
    since: str
    neighbor_address: str
    neighbor_as: int
    description: str

@dataclass
class PeerStatus:
    asn: str
    description: str
    sessions: Dict[str, Dict[str, List[BGPSession]]]  # {afi: {ix: [sessions]}}
    
class PeeringDashboard:
    def __init__(self):
        self.config = self.load_config()
        self.session_cache = {}
        self.cache_timestamp = 0
        self.cache_ttl = 60  # Cache for 1 minute
        
    def load_config(self) -> Dict:
        """Load configuration from config.yaml"""
        try:
            with open('config.yaml', 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            # Default configuration
            return {
                'session_definition_url': 'https://raw.githubusercontent.com/poweredgenl/networkstuff/main/peering/peers_as200132.yaml',
                'routers': ['195.95.177.2', '195.95.177.3'],
                'ixps': {
                    'amsix': {
                        'pretty_name': 'AMS-IX',
                        'ipv4_range': ['80.249.208.0', '80.249.215.254'],
                        'ipv6_range': ['2001:7f8:1:0:0:0:0:0', '2001:7f8:1:0:ffff:ffff:ffff:ffff']
                    },
                    'frys-ix': {
                        'pretty_name': 'Frys-IX', 
                        'ipv4_range': ['185.1.160.0', '185.1.161.255'],
                        'ipv6_range': ['2001:7f8:10f:0:0:0:0:0', '2001:7f8:10f:0:ffff:ffff:ffff:ffff']
                    },
                    'speedix': {
                        'pretty_name': 'SpeedIX',
                        'ipv4_range': ['185.1.222.0', '185.1.223.255'],
                        'ipv6_range': ['2001:7f8:b7:0:0:0:0:0', '2001:7f8:b7:0:ffff:ffff:ffff:ffff']
                    },
                    'nlix': {
                        'pretty_name': 'NL-IX',
                        'ipv4_range': ['193.239.116.0', '193.239.119.255'],
                        'ipv6_range': ['2001:7f8:13:0:0:0:0:0', '2001:7f8:13:0:ffff:ffff:ffff:ffff']
                    },
                    'loc-ix': {
                        'pretty_name': 'Loc-IX',
                        'ipv4_range': ['185.1.138.0', '185.1.138.255'],
                        'ipv6_range': ['2a0c:b641:700:0:0:0:0:0', '2a0c:b641:700:0:ffff:ffff:ffff:ffff']
                    },
                    'interix': {
                        'pretty_name': 'InterIX',
                        'ipv4_range': ['185.0.1.0', '185.0.1.255'],
                        'ipv6_range': ['2001:7f8:134:0:0:0:0:0', '2001:7f8:134:0:ffff:ffff:ffff:ffff']
                    },
                    'lsix': {
                        'pretty_name': 'LayerswitchIX',
                        'ipv4_range': ['185.1.32.0', '185.1.32.255'],
                        'ipv6_range': ['2001:7f8:8f:0:0:0:0:0', '2001:7f8:8f:0:ffff:ffff:ffff:ffff']
                    },
                    'fogixp': {
                        'pretty_name': 'FogIXP',
                        'ipv4_range': ['185.1.147.0', '185.1.147.255'],
                        'ipv6_range': ['2001:7f8:ca:1:0:0:0:0', '2001:7f8:ca:1:ffff:ffff:ffff:ffff']
                    }
                },
                'warning_thresholds': {
                    'short': 86400,  # 1 day
                    'long': 604800   # 1 week
                }
            }
    
    def ip_to_ix(self, ip_address: str, afi: str) -> Optional[str]:
        """Determine which IXP an IP address belongs to"""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            for ix_name, ix_config in self.config['ixps'].items():
                if afi == 'ipv4' and ip.version == 4:
                    start_ip = ipaddress.ip_address(ix_config['ipv4_range'][0])
                    end_ip = ipaddress.ip_address(ix_config['ipv4_range'][1])
                    if start_ip <= ip <= end_ip:
                        return ix_name
                elif afi == 'ipv6' and ip.version == 6:
                    start_ip = ipaddress.ip_address(ix_config['ipv6_range'][0])
                    end_ip = ipaddress.ip_address(ix_config['ipv6_range'][1])
                    if start_ip <= ip <= end_ip:
                        return ix_name
            
            return None
        except ValueError:
            logger.error(f"Invalid IP address: {ip_address}")
            return None
    
    async def fetch_router_sessions(self, session: aiohttp.ClientSession, router: str, port: int) -> Dict:
        """Fetch BGP sessions from a router"""
        try:
            url = f"http://{router}:{port}/protocols/bgp"
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('protocols', {})
                else:
                    logger.error(f"HTTP {response.status} from {router}:{port}")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching from {router}:{port}: {e}")
            return {}
    
    async def fetch_session_definition(self, session: aiohttp.ClientSession) -> Dict:
        """Fetch peer definitions from GitHub"""
        try:
            url = self.config['session_definition_url']
            async with session.get(url, timeout=30) as response:
                if response.status == 200:
                    yaml_content = await response.text()
                    return yaml.safe_load(yaml_content)
                else:
                    logger.error(f"HTTP {response.status} from session definition URL")
                    return {}
        except Exception as e:
            logger.error(f"Error fetching session definitions: {e}")
            return {}
    
    async def collect_all_sessions(self) -> Dict[str, PeerStatus]:
        """Collect BGP sessions from all routers and merge with definitions"""
        async with aiohttp.ClientSession() as session:
            # Fetch session definitions
            defined_sessions = await self.fetch_session_definition(session)
            
            # Fetch live sessions from routers
            router_tasks = []
            for router in self.config['routers']:
                router_tasks.append(self.fetch_router_sessions(session, router, 29184))  # IPv4
                router_tasks.append(self.fetch_router_sessions(session, router, 29186))  # IPv6
            
            router_results = await asyncio.gather(*router_tasks)
            
            # Process results
            ipv4_sessions = {}
            ipv6_sessions = {}
            
            for i, result in enumerate(router_results):
                router_idx = i // 2
                afi = 'ipv4' if i % 2 == 0 else 'ipv6'
                router = self.config['routers'][router_idx]
                
                if afi == 'ipv4':
                    ipv4_sessions[router] = result
                else:
                    ipv6_sessions[router] = result
            
            # Merge live sessions with definitions
            peer_statuses = {}
            
            for asn, peer_data in defined_sessions.items():
                peer_status = PeerStatus(
                    asn=asn,
                    description=peer_data.get('description', ''),
                    sessions={'ipv4': {}, 'ipv6': {}}
                )
                
                # Process live sessions
                for afi, afi_sessions in [('ipv4', ipv4_sessions), ('ipv6', ipv6_sessions)]:
                    for router, sessions in afi_sessions.items():
                        for session_name, session_data in sessions.items():
                            if str(session_data.get('neighbor_as')) == asn.replace('AS', ''):
                                # Determine IXP
                                neighbor_ip = session_data.get('neighbor_address')
                                ix_name = self.ip_to_ix(neighbor_ip, afi)
                                
                                if ix_name:
                                    if ix_name not in peer_status.sessions[afi]:
                                        peer_status.sessions[afi][ix_name] = []
                                    
                                    bgp_session = BGPSession(
                                        state=session_data.get('bgp_state', 'Unknown'),
                                        since=session_data.get('state_changed', ''),
                                        neighbor_address=neighbor_ip,
                                        neighbor_as=session_data.get('neighbor_as'),
                                        description=session_data.get('description', '')
                                    )
                                    
                                    peer_status.sessions[afi][ix_name].append(bgp_session)
                
                peer_statuses[asn] = peer_status
            
            return peer_statuses
    
    def get_session_status_class(self, session: BGPSession) -> str:
        """Get CSS class for session status"""
        if session.state == 'Established':
            return 'success'
        
        try:
            since_time = datetime.fromisoformat(session.since.replace('Z', '+00:00'))
            age = (datetime.now() - since_time).total_seconds()
            
            if age < self.config['warning_thresholds']['short']:
                return 'warning'
            elif age < self.config['warning_thresholds']['long']:
                return 'info'
            else:
                return 'danger'
        except:
            return 'secondary'
    
    def filter_peers(self, peers: Dict[str, PeerStatus], filters: Dict) -> Dict[str, PeerStatus]:
        """Filter peers based on request parameters"""
        filtered = {}
        
        for asn, peer in peers.items():
            # ASN filter
            if filters.get('asn'):
                asn_number = asn.replace('AS', '')
                if filters['asn'] not in asn_number:
                    continue
            
            # Peer name filter
            if filters.get('peername'):
                if filters['peername'].lower() not in peer.description.lower():
                    continue
            
            # State filters for each IXP/AFI combination
            should_include = True
            for ix_name in self.config['ixps'].keys():
                for afi in ['ipv4', 'ipv6']:
                    filter_key = f"{ix_name}_{afi}"
                    filter_value = filters.get(filter_key)
                    
                    if filter_value and filter_value != 'any':
                        ix_sessions = peer.sessions.get(afi, {}).get(ix_name, [])
                        
                        if filter_value == 'established':
                            if not any(s.state == 'Established' for s in ix_sessions):
                                should_include = False
                                break
                        elif filter_value == 'configured':
                            if not ix_sessions:
                                should_include = False
                                break
                        elif filter_value == 'not_connected':
                            if not any(s.state != 'Established' for s in ix_sessions):
                                should_include = False
                                break
                        elif filter_value == 'not_configured':
                            if ix_sessions:
                                should_include = False
                                break
                
                if not should_include:
                    break
            
            if should_include:
                filtered[asn] = peer
        
        return filtered
    
    async def get_peers_data(self, use_cache: bool = True) -> Dict[str, PeerStatus]:
        """Get peers data with caching"""
        current_time = time.time()
        
        if use_cache and self.session_cache and (current_time - self.cache_timestamp) < self.cache_ttl:
            return self.session_cache
        
        try:
            self.session_cache = await self.collect_all_sessions()
            self.cache_timestamp = current_time
            return self.session_cache
        except Exception as e:
            logger.error(f"Error collecting sessions: {e}")
            # Return cached data if available, even if stale
            return self.session_cache if self.session_cache else {}

# Global dashboard instance
dashboard = PeeringDashboard()

@app.route('/')
async def index():
    """Main peering dashboard page"""
    # Get filter parameters
    filters = {
        'asn': request.args.get('asn', ''),
        'peername': request.args.get('peername', ''),
        'ixes': request.args.get('ixes', '').split(',') if request.args.get('ixes') else None
    }
    
    # Add IXP-specific filters
    for ix_name in dashboard.config['ixps'].keys():
        for afi in ['ipv4', 'ipv6']:
            filter_key = f"{ix_name}_{afi}"
            filters[filter_key] = request.args.get(filter_key, 'any')
    
    # Get peers data
    peers = await dashboard.get_peers_data()
    
    # Apply filters
    if any(v for v in filters.values() if v and v != 'any'):
        peers = dashboard.filter_peers(peers, filters)
    
    # Sort peers
    sort_column = request.args.get('sort', 'asn')
    sort_direction = request.args.get('sortdir', 'asc')
    
    if sort_column == 'name':
        peers = dict(sorted(peers.items(), 
                          key=lambda x: x[1].description.lower(),
                          reverse=(sort_direction == 'desc')))
    else:  # Default to ASN sort
        peers = dict(sorted(peers.items(),
                          key=lambda x: int(x[0].replace('AS', '')),
                          reverse=(sort_direction == 'desc')))
    
    return render_template('index.html', 
                         peers=peers,
                         ixps=dashboard.config['ixps'],
                         filters=filters,
                         sort_column=sort_column,
                         sort_direction=sort_direction,
                         dashboard=dashboard)

@app.route('/api/peers')
async def api_peers():
    """API endpoint for peers data"""
    peers = await dashboard.get_peers_data()
    
    # Convert to JSON-serializable format
    peers_json = {}
    for asn, peer in peers.items():
        peers_json[asn] = asdict(peer)
    
    return jsonify(peers_json)

@app.route('/api/peer/<asn>')
async def api_peer_detail(asn):
    """API endpoint for specific peer details"""
    peers = await dashboard.get_peers_data()
    
    if asn in peers:
        return jsonify(asdict(peers[asn]))
    else:
        return jsonify({'error': 'Peer not found'}), 404

@app.route('/api/summary')
async def api_summary():
    """API endpoint for dashboard summary"""
    peers = await dashboard.get_peers_data()
    
    summary = {
        'total_peers': len(peers),
        'established_sessions': 0,
        'down_sessions': 0,
        'ixp_summary': {},
        'timestamp': datetime.now().isoformat()
    }
    
    for ix_name, ix_config in dashboard.config['ixps'].items():
        summary['ixp_summary'][ix_name] = {
            'name': ix_config['pretty_name'],
            'established': 0,
            'down': 0
        }
    
    for peer in peers.values():
        for afi in ['ipv4', 'ipv6']:
            for ix_name, sessions in peer.sessions.get(afi, {}).items():
                for session in sessions:
                    if session.state == 'Established':
                        summary['established_sessions'] += 1
                        if ix_name in summary['ixp_summary']:
                            summary['ixp_summary'][ix_name]['established'] += 1
                    else:
                        summary['down_sessions'] += 1
                        if ix_name in summary['ixp_summary']:
                            summary['ixp_summary'][ix_name]['down'] += 1
    
    return jsonify(summary)

@app.route('/api/version')
def api_version():
    """API endpoint for version information"""
    return jsonify(get_version_info())

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        'status': 'healthy',
        'version': get_version(),
        'timestamp': datetime.now().isoformat(),
        'service': 'peerview'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)