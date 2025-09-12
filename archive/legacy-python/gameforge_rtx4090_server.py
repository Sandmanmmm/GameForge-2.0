#!/usr/bin/env python3
"""
GameForge RTX 4090 Server - Production Version
Enhanced for VS Code integration with comprehensive API endpoints
"""

import json
import time
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys
import os

class GameForgeRTX4090Handler(BaseHTTPRequestHandler):
    """Enhanced HTTP handler for RTX 4090 operations with VS Code support."""
    
    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response with proper headers."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def _get_gpu_info(self):
        """Get comprehensive GPU information."""
        try:
            import torch
            
            gpu_info = {
                'available': torch.cuda.is_available(),
                'device_count': torch.cuda.device_count(),
                'timestamp': time.time()
            }
            
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                props = torch.cuda.get_device_properties(device)
                
                gpu_info.update({
                    'name': torch.cuda.get_device_name(device),
                    'memory_total': props.total_memory,
                    'memory_total_gb': round(props.total_memory / 1024**3, 1),
                    'memory_allocated': torch.cuda.memory_allocated(device),
                    'memory_cached': torch.cuda.memory_reserved(device),
                    'multiprocessor_count': props.multiprocessor_count,
                    'cuda_capability': f"{props.major}.{props.minor}",
                    'pytorch_version': torch.__version__
                })
                
                # Calculate memory percentages
                gpu_info['memory_allocated_percent'] = (gpu_info['memory_allocated'] / gpu_info['memory_total']) * 100
                gpu_info['memory_cached_percent'] = (gpu_info['memory_cached'] / gpu_info['memory_total']) * 100
                
                # Try to get nvidia-smi info
                try:
                    import subprocess
                    result = subprocess.run([
                        'nvidia-smi', 
                        '--query-gpu=utilization.gpu,utilization.memory,temperature.gpu,power.draw',
                        '--format=csv,noheader,nounits'
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        values = result.stdout.strip().split(', ')
                        gpu_info.update({
                            'utilization_gpu': float(values[0]),
                            'utilization_memory': float(values[1]),
                            'temperature': float(values[2]),
                            'power_draw': float(values[3])
                        })
                except Exception as e:
                    gpu_info['nvidia_smi_error'] = str(e)
            
            return gpu_info
            
        except ImportError:
            return {'available': False, 'error': 'PyTorch not available'}
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def _execute_python_code(self, code):
        """Execute Python code and capture output."""
        try:
            # Capture stdout and stderr
            from io import StringIO
            import contextlib
            
            stdout_capture = StringIO()
            stderr_capture = StringIO()
            
            # Create execution environment with torch available
            exec_globals = {
                '__name__': '__main__',
                '__builtins__': __builtins__,
            }
            
            # Try to import common libraries
            try:
                import torch
                exec_globals['torch'] = torch
            except ImportError:
                pass
            
            try:
                import numpy as np
                exec_globals['np'] = np
                exec_globals['numpy'] = np
            except ImportError:
                pass
            
            try:
                import json as json_module
                exec_globals['json'] = json_module
            except ImportError:
                pass
            
            # Execute the code
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(code, exec_globals)
            
            stdout_result = stdout_capture.getvalue()
            stderr_result = stderr_capture.getvalue()
            
            result = {
                'success': True,
                'output': stdout_result,
                'error': stderr_result if stderr_result else None,
                'timestamp': time.time()
            }
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'output': None,
                'error': f"{type(e).__name__}: {str(e)}",
                'traceback': traceback.format_exc(),
                'timestamp': time.time()
            }
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/health' or path == '/':
                # Health check endpoint
                gpu_info = self._get_gpu_info()
                response = {
                    'status': 'healthy',
                    'server': 'GameForge RTX 4090',
                    'instance_id': '25599851',
                    'gpu': gpu_info,
                    'endpoints': [
                        '/health - Server health check',
                        '/gpu - GPU status and metrics',
                        '/execute - Execute Python code (POST)',
                        '/vscode - VS Code integration info'
                    ],
                    'timestamp': time.time()
                }
                self._send_json_response(response)
                
            elif path == '/gpu':
                # GPU status endpoint
                gpu_info = self._get_gpu_info()
                self._send_json_response(gpu_info)
                
            elif path == '/vscode':
                # VS Code integration information
                integration_info = {
                    'tunnel_url': 'https://moisture-simply-arab-fires.trycloudflare.com',
                    'instance_id': '25599851',
                    'gpu_model': 'RTX 4090',
                    'python_path': '/venv/main/bin/python',
                    'workspace_path': '/workspace',
                    'magic_commands': {
                        '%gpu_status': 'Check GPU status',
                        '%%gpu_exec': 'Execute code on GPU'
                    },
                    'jupyter_kernel': {
                        'display_name': 'Vast.ai RTX 4090',
                        'language': 'python',
                        'env': {
                            'CUDA_VISIBLE_DEVICES': '0',
                            'PYTORCH_CUDA_ALLOC_CONF': 'max_split_size_mb:128'
                        }
                    }
                }
                self._send_json_response(integration_info)
                
            else:
                # 404 for unknown paths
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'Endpoint not found')
                
        except Exception as e:
            error_response = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': time.time()
            }
            self._send_json_response(error_response, status_code=500)
    
    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        try:
            if path == '/execute':
                # Code execution endpoint
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    request_data = json.loads(post_data.decode('utf-8'))
                    code = request_data.get('code', '')
                    language = request_data.get('language', 'python')
                    
                    if language != 'python':
                        response = {
                            'success': False,
                            'error': f'Unsupported language: {language}',
                            'supported_languages': ['python']
                        }
                    else:
                        response = self._execute_python_code(code)
                        
                    self._send_json_response(response)
                    
                except json.JSONDecodeError:
                    error_response = {
                        'success': False,
                        'error': 'Invalid JSON in request body',
                        'expected_format': {
                            'code': 'Python code to execute',
                            'language': 'python'
                        }
                    }
                    self._send_json_response(error_response, status_code=400)
                    
            else:
                # 404 for unknown POST paths
                self.send_response(404)
                self._set_cors_headers()
                self.end_headers()
                self.wfile.write(b'POST endpoint not found')
                
        except Exception as e:
            error_response = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
                'timestamp': time.time()
            }
            self._send_json_response(error_response, status_code=500)
    
    def log_message(self, format, *args):
        """Custom log format."""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] GameForge RTX 4090 - {format % args}")

def run_server(port=8000, host='0.0.0.0'):
    """Run the GameForge RTX 4090 server."""
    print(f"🚀 Starting GameForge RTX 4090 Server...")
    print(f"🔗 Host: {host}:{port}")
    print(f"🎮 GPU: RTX 4090 (Instance 25599851)")
    print(f"🌐 Tunnel: https://moisture-simply-arab-fires.trycloudflare.com")
    print(f"🔧 VS Code Integration: Ready")
    
    try:
        server = HTTPServer((host, port), GameForgeRTX4090Handler)
        print(f"✅ Server running on {host}:{port}")
        print(f"📊 Health check: http://{host}:{port}/health")
        print(f"🎯 GPU status: http://{host}:{port}/gpu")
        print(f"💻 VS Code info: http://{host}:{port}/vscode")
        print(f"⚡ Code execution: POST http://{host}:{port}/execute")
        print("🔄 Server ready for requests...")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # Default to port 8000 for Cloudflare tunnel
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port=port, host='0.0.0.0')
