#!/usr/bin/env python3
"""
GameForge AI Container Image Signing with Cosign
Enterprise-grade image signing and verification for supply chain security
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "cosign_signer", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class CosignSigner:
    """Container image signing and verification with Cosign"""
    
    def __init__(self):
        self.cosign_experimental = os.getenv('COSIGN_EXPERIMENTAL', '1')
        self.registry = os.getenv('REGISTRY', 'ghcr.io')
        self.image_name = os.getenv('IMAGE_NAME', 'gameforge/ai-platform')
        self.key_path = os.getenv('COSIGN_KEY_PATH', './cosign.key')
        self.pub_key_path = os.getenv('COSIGN_PUBLIC_KEY_PATH', './cosign.pub')
    
    def install_cosign(self) -> bool:
        """Install Cosign binary"""
        try:
            logger.info("🔧 Installing Cosign...")
            
            # Check if already installed
            result = subprocess.run(
                ["cosign", "version"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Cosign already installed: {result.stdout.strip()}")
                return True
            
            # Download and install Cosign
            subprocess.run([
                "curl", "-O", "-L", 
                "https://github.com/sigstore/cosign/releases/latest/download/cosign-linux-amd64"
            ], check=True)
            
            subprocess.run([
                "sudo", "mv", "cosign-linux-amd64", "/usr/local/bin/cosign"
            ], check=True)
            
            subprocess.run([
                "sudo", "chmod", "+x", "/usr/local/bin/cosign"
            ], check=True)
            
            # Verify installation
            result = subprocess.run(
                ["cosign", "version"],
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"✅ Cosign installed: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Cosign installation failed: {e}")
            return False
    
    def generate_key_pair(self, password: Optional[str] = None) -> bool:
        """Generate Cosign key pair for signing"""
        try:
            logger.info("🔑 Generating Cosign key pair...")
            
            # Check if keys already exist
            if Path(self.key_path).exists() and Path(self.pub_key_path).exists():
                logger.info("✅ Cosign key pair already exists")
                return True
            
            # Set environment for key generation
            env = os.environ.copy()
            if password:
                env['COSIGN_PASSWORD'] = password
            else:
                env['COSIGN_PASSWORD'] = ''  # Empty password for automation
            
            # Generate key pair
            subprocess.run([
                "cosign", "generate-key-pair"
            ], env=env, check=True)
            
            logger.info(f"✅ Key pair generated: {self.key_path}, {self.pub_key_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Key pair generation failed: {e}")
            return False
    
    def sign_image_keyless(self, image_ref: str) -> bool:
        """Sign image using keyless signing (OIDC)"""
        try:
            logger.info(f"🔐 Signing image keyless: {image_ref}")
            
            # Set experimental mode for keyless signing
            env = os.environ.copy()
            env['COSIGN_EXPERIMENTAL'] = '1'
            
            # Sign the image
            subprocess.run([
                "cosign", "sign", "--yes", image_ref
            ], env=env, check=True)
            
            logger.info("✅ Image signed with keyless signing")
            return True
            
        except Exception as e:
            logger.error(f"❌ Keyless signing failed: {e}")
            return False
    
    def sign_image_with_key(self, image_ref: str, key_path: str, password: Optional[str] = None) -> bool:
        """Sign image using private key"""
        try:
            logger.info(f"🔐 Signing image with key: {image_ref}")
            
            if not Path(key_path).exists():
                logger.error(f"❌ Private key not found: {key_path}")
                return False
            
            # Set environment for signing
            env = os.environ.copy()
            if password:
                env['COSIGN_PASSWORD'] = password
            else:
                env['COSIGN_PASSWORD'] = ''
            
            # Sign the image
            subprocess.run([
                "cosign", "sign", "--key", key_path, image_ref
            ], env=env, check=True)
            
            logger.info("✅ Image signed with private key")
            return True
            
        except Exception as e:
            logger.error(f"❌ Key-based signing failed: {e}")
            return False
    
    def verify_signature_keyless(self, image_ref: str) -> bool:
        """Verify image signature using keyless verification"""
        try:
            logger.info(f"🔍 Verifying keyless signature: {image_ref}")
            
            # Set experimental mode
            env = os.environ.copy()
            env['COSIGN_EXPERIMENTAL'] = '1'
            
            # Verify the signature
            result = subprocess.run([
                "cosign", "verify", 
                "--certificate-identity-regexp", ".*",
                "--certificate-oidc-issuer", "https://token.actions.githubusercontent.com",
                image_ref
            ], env=env, capture_output=True, text=True, check=True)
            
            logger.info("✅ Keyless signature verification passed")
            logger.info(f"Verification details: {result.stdout}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Keyless verification failed: {e}")
            return False
    
    def verify_signature_with_key(self, image_ref: str, public_key_path: str) -> bool:
        """Verify image signature using public key"""
        try:
            logger.info(f"🔍 Verifying signature with public key: {image_ref}")
            
            if not Path(public_key_path).exists():
                logger.error(f"❌ Public key not found: {public_key_path}")
                return False
            
            # Verify the signature
            result = subprocess.run([
                "cosign", "verify", "--key", public_key_path, image_ref
            ], capture_output=True, text=True, check=True)
            
            logger.info("✅ Key-based signature verification passed")
            logger.info(f"Verification details: {result.stdout}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Key-based verification failed: {e}")
            return False
    
    def generate_attestation(self, image_ref: str, attestation_data: Dict[str, Any]) -> bool:
        """Generate and attach SLSA attestation to image"""
        try:
            logger.info(f"📋 Generating attestation for: {image_ref}")
            
            # Create attestation file
            attestation_file = Path("attestation.json")
            with open(attestation_file, 'w') as f:
                json.dump(attestation_data, f, indent=2)
            
            # Set experimental mode
            env = os.environ.copy()
            env['COSIGN_EXPERIMENTAL'] = '1'
            
            # Generate attestation
            subprocess.run([
                "cosign", "attest", "--yes",
                "--predicate", str(attestation_file),
                image_ref
            ], env=env, check=True)
            
            # Cleanup
            attestation_file.unlink()
            
            logger.info("✅ Attestation generated and attached")
            return True
            
        except Exception as e:
            logger.error(f"❌ Attestation generation failed: {e}")
            return False
    
    def verify_attestation(self, image_ref: str) -> bool:
        """Verify SLSA attestation"""
        try:
            logger.info(f"🔍 Verifying attestation: {image_ref}")
            
            # Set experimental mode
            env = os.environ.copy()
            env['COSIGN_EXPERIMENTAL'] = '1'
            
            # Verify attestation
            result = subprocess.run([
                "cosign", "verify-attestation",
                "--certificate-identity-regexp", ".*",
                "--certificate-oidc-issuer", "https://token.actions.githubusercontent.com",
                image_ref
            ], env=env, capture_output=True, text=True, check=True)
            
            logger.info("✅ Attestation verification passed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Attestation verification failed: {e}")
            return False
    
    def get_image_signatures(self, image_ref: str) -> List[Dict[str, Any]]:
        """Get all signatures for an image"""
        try:
            logger.info(f"🔍 Getting signatures for: {image_ref}")
            
            # Get signatures
            result = subprocess.run([
                "cosign", "tree", image_ref
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"Image signature tree:\n{result.stdout}")
            
            # Parse and return structured data
            signatures = []
            for line in result.stdout.split('\n'):
                if 'signature' in line.lower():
                    signatures.append({
                        "type": "signature",
                        "details": line.strip()
                    })
                elif 'attestation' in line.lower():
                    signatures.append({
                        "type": "attestation", 
                        "details": line.strip()
                    })
            
            return signatures
            
        except Exception as e:
            logger.error(f"❌ Failed to get signatures: {e}")
            return []
    
    def create_slsa_attestation(self, image_ref: str, build_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create SLSA provenance attestation"""
        attestation = {
            "_type": "https://in-toto.io/Statement/v0.1",
            "predicateType": "https://slsa.dev/provenance/v0.2",
            "subject": [
                {
                    "name": image_ref,
                    "digest": {
                        "sha256": build_info.get("image_digest", "")
                    }
                }
            ],
            "predicate": {
                "builder": {
                    "id": "https://github.com/actions/runner"
                },
                "buildType": "github-actions",
                "invocation": {
                    "configSource": {
                        "uri": build_info.get("repo_url", ""),
                        "digest": {
                            "sha1": build_info.get("commit_sha", "")
                        }
                    }
                },
                "metadata": {
                    "buildInvocationId": build_info.get("run_id", ""),
                    "buildStartedOn": build_info.get("build_timestamp", datetime.now().isoformat()),
                    "buildFinishedOn": datetime.now().isoformat(),
                    "completeness": {
                        "parameters": True,
                        "environment": False,
                        "materials": True
                    },
                    "reproducible": False
                },
                "materials": [
                    {
                        "uri": build_info.get("repo_url", ""),
                        "digest": {
                            "sha1": build_info.get("commit_sha", "")
                        }
                    }
                ]
            }
        }
        
        return attestation
    
    def sign_and_verify_complete_workflow(self, image_ref: str, use_keyless: bool = True) -> bool:
        """Complete signing and verification workflow"""
        try:
            logger.info(f"🚀 Starting complete signing workflow for: {image_ref}")
            
            # Install Cosign if needed
            if not self.install_cosign():
                return False
            
            success = True
            
            if use_keyless:
                # Keyless signing workflow
                logger.info("Using keyless signing...")
                
                # Sign image
                if not self.sign_image_keyless(image_ref):
                    success = False
                
                # Create and attach SLSA attestation
                build_info = {
                    "repo_url": os.getenv("GITHUB_SERVER_URL", "") + "/" + os.getenv("GITHUB_REPOSITORY", ""),
                    "commit_sha": os.getenv("GITHUB_SHA", ""),
                    "run_id": os.getenv("GITHUB_RUN_ID", ""),
                    "image_digest": image_ref.split("@")[-1] if "@" in image_ref else "",
                    "build_timestamp": datetime.now().isoformat()
                }
                
                attestation = self.create_slsa_attestation(image_ref, build_info)
                if not self.generate_attestation(image_ref, attestation):
                    success = False
                
                # Verify signature
                if not self.verify_signature_keyless(image_ref):
                    success = False
                
                # Verify attestation
                if not self.verify_attestation(image_ref):
                    success = False
                
            else:
                # Key-based signing workflow
                logger.info("Using key-based signing...")
                
                # Generate key pair if needed
                if not self.generate_key_pair():
                    return False
                
                # Sign image
                if not self.sign_image_with_key(image_ref, self.key_path):
                    success = False
                
                # Verify signature
                if not self.verify_signature_with_key(image_ref, self.pub_key_path):
                    success = False
            
            # Get signature information
            signatures = self.get_image_signatures(image_ref)
            logger.info(f"📋 Total signatures/attestations: {len(signatures)}")
            
            if success:
                logger.info("🎉 Complete signing workflow succeeded")
            else:
                logger.error("❌ Signing workflow had failures")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Complete signing workflow failed: {e}")
            return False

async def main():
    """Main Cosign signing function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GameForge AI Container Image Signer')
    parser.add_argument('--install', action='store_true', help='Install Cosign')
    parser.add_argument('--generate-keys', action='store_true', help='Generate signing key pair')
    parser.add_argument('--sign', help='Sign specified image reference')
    parser.add_argument('--verify', help='Verify specified image reference')
    parser.add_argument('--keyless', action='store_true', help='Use keyless signing/verification')
    parser.add_argument('--complete-workflow', help='Run complete sign and verify workflow')
    parser.add_argument('--image-ref', help='Image reference to sign/verify')
    parser.add_argument('--password', help='Password for private key (if using key-based signing)')
    
    args = parser.parse_args()
    
    signer = CosignSigner()
    
    try:
        if args.install:
            success = signer.install_cosign()
            sys.exit(0 if success else 1)
        
        if args.generate_keys:
            success = signer.generate_key_pair(args.password)
            sys.exit(0 if success else 1)
        
        if args.sign:
            image_ref = args.sign
            if args.keyless:
                success = signer.sign_image_keyless(image_ref)
            else:
                success = signer.sign_image_with_key(image_ref, signer.key_path, args.password)
            sys.exit(0 if success else 1)
        
        if args.verify:
            image_ref = args.verify
            if args.keyless:
                success = signer.verify_signature_keyless(image_ref)
            else:
                success = signer.verify_signature_with_key(image_ref, signer.pub_key_path)
            sys.exit(0 if success else 1)
        
        if args.complete_workflow:
            image_ref = args.complete_workflow
            success = signer.sign_and_verify_complete_workflow(image_ref, args.keyless)
            sys.exit(0 if success else 1)
        
        # Default: show usage
        parser.print_help()
        
    except Exception as e:
        logger.error(f"❌ Cosign operation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())