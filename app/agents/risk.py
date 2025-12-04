from typing import Any, Dict, List
from app.agents.base import BaseAgent
import re


class RiskAgent(BaseAgent):
    """Calculates risk score based on multiple factors including security checks."""
    
    # Sensitive file patterns
    SENSITIVE_FILES = {
        '.env', '.env.local', '.env.production',
        'secrets.yaml', 'secrets.yml', 'secrets.json',
        'credentials.json', 'service-account.json',
        'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
        '.pem', '.key', '.pfx', '.p12',
    }
    
    SENSITIVE_PATHS = [
        r'config/secrets',
        r'\.aws/',
        r'\.ssh/',
        r'private[_-]?key',
    ]
    
    # Dangerous code patterns
    SECURITY_PATTERNS = {
        'hardcoded_secret': [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
            r'AWS[_-]?SECRET[_-]?ACCESS[_-]?KEY',
        ],
        'sql_injection': [
            r'execute\s*\(\s*["\'].*\%s',
            r'cursor\.execute\s*\([^,]+\+',
            r'query\s*=.*\+.*input',
            r'f["\']SELECT.*\{',
        ],
        'command_injection': [
            r'os\.system\s*\(',
            r'subprocess\.call\s*\([^,]+shell\s*=\s*True',
            r'eval\s*\(',
            r'exec\s*\(',
        ],
        'xss_risk': [
            r'innerHTML\s*=',
            r'dangerouslySetInnerHTML',
            r'document\.write\s*\(',
        ],
        'insecure_crypto': [
            r'md5\s*\(',
            r'sha1\s*\(',
            r'DES\s*\(',
            r'random\.random\s*\(\)',  # Not cryptographically secure
        ],
    }
    
    # Known vulnerable/deprecated packages
    VULNERABLE_PACKAGES = {
        'python': ['pycrypto', 'python-jwt', 'pyyaml<5.4'],
        'javascript': ['event-stream', 'flatmap-stream', 'ua-parser-js<0.7.28'],
    }

    async def run(self) -> Dict[str, Any]:
        print("RiskAgent: Calculating risk...")
        
        diff_data = self.context.get("diff_data", {})
        test_data = self.context.get("test_data", {})
        dependency_data = self.context.get("dependency_data", {})
        
        score = 0
        reasons = []
        security_issues = []
        
        files_changed = diff_data.get("files_changed", [])
        
        # ===== SIZE FACTORS =====
        
        # 1. Number of files changed
        changes = diff_data.get("changed_files_count", len(files_changed))
        if changes > 10:
            score += 25
            reasons.append(f"Large PR ({changes} files)")
        elif changes > 5:
            score += 10
            reasons.append(f"Medium-sized PR ({changes} files)")
        
        # 2. Lines of code changed
        additions = diff_data.get("total_additions", 0)
        deletions = diff_data.get("total_deletions", 0)
        total_lines = additions + deletions
        
        if total_lines > 500:
            score += 20
            reasons.append(f"Many lines changed ({total_lines})")
        elif total_lines > 200:
            score += 10
            reasons.append(f"Moderate lines changed ({total_lines})")
        
        # 3. Missing tests
        if test_data.get("missing_tests"):
            score += 25
            reasons.append("No tests modified")
        
        # 4. Cross-file impact
        impact_analysis = dependency_data.get("impact_analysis", [])
        if len(impact_analysis) > 5:
            score += 15
            reasons.append(f"High impact ({len(impact_analysis)} files may be affected)")
        elif len(impact_analysis) > 0:
            score += 5
            reasons.append(f"Some impact ({len(impact_analysis)} files may be affected)")
        
        # ===== SECURITY FACTORS =====
        
        for file_info in files_changed:
            filename = file_info.get("filename", "")
            patch = file_info.get("patch", "")
            
            # 5. Sensitive file detection
            if self._is_sensitive_file(filename):
                score += 30
                security_issues.append(f"🔴 Sensitive file modified: `{filename}`")
            
            # 6. Security pattern detection in code
            patterns_found = self._check_security_patterns(patch, filename)
            for issue in patterns_found:
                score += 20
                security_issues.append(issue)
            
            # 7. Vulnerable package detection
            if filename in ['requirements.txt', 'package.json', 'Pipfile', 'go.mod']:
                vulns = self._check_vulnerable_packages(patch, filename)
                for vuln in vulns:
                    score += 25
                    security_issues.append(vuln)
        
        # Determine level
        if score >= 70:
            level = "Critical"
        elif score >= 50:
            level = "High"
        elif score >= 30:
            level = "Medium"
        else:
            level = "Low"
        
        return {
            "score": min(score, 100),
            "level": level,
            "reasons": reasons,
            "security_issues": security_issues
        }
    
    def _is_sensitive_file(self, filename: str) -> bool:
        """Check if a file is sensitive."""
        # Check exact matches
        basename = filename.split('/')[-1]
        if basename in self.SENSITIVE_FILES:
            return True
        
        # Check extensions
        for ext in ['.pem', '.key', '.pfx', '.p12']:
            if filename.endswith(ext):
                return True
        
        # Check path patterns
        for pattern in self.SENSITIVE_PATHS:
            if re.search(pattern, filename, re.IGNORECASE):
                return True
        
        return False
    
    def _check_security_patterns(self, patch: str, filename: str) -> List[str]:
        """Scan code for security issues."""
        issues = []
        
        if not patch:
            return issues
        
        # Only check added lines (start with +)
        added_lines = [line for line in patch.split('\n') if line.startswith('+')]
        added_code = '\n'.join(added_lines)
        
        for category, patterns in self.SECURITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, added_code, re.IGNORECASE):
                    issue_names = {
                        'hardcoded_secret': '🔑 Potential hardcoded secret',
                        'sql_injection': '💉 Potential SQL injection',
                        'command_injection': '⚠️ Potential command injection',
                        'xss_risk': '🌐 Potential XSS vulnerability',
                        'insecure_crypto': '🔓 Insecure cryptography',
                    }
                    issues.append(f"{issue_names.get(category, category)} in `{filename}`")
                    break  # One per category per file
        
        return issues
    
    def _check_vulnerable_packages(self, patch: str, filename: str) -> List[str]:
        """Check for known vulnerable packages."""
        issues = []
        
        if not patch:
            return issues
        
        if 'requirements.txt' in filename or 'Pipfile' in filename:
            for pkg in self.VULNERABLE_PACKAGES.get('python', []):
                pkg_name = pkg.split('<')[0].split('>')[0].split('=')[0]
                if pkg_name.lower() in patch.lower():
                    issues.append(f"📦 Potentially vulnerable package: `{pkg_name}`")
        
        elif 'package.json' in filename:
            for pkg in self.VULNERABLE_PACKAGES.get('javascript', []):
                pkg_name = pkg.split('<')[0].split('>')[0].split('@')[0]
                if pkg_name.lower() in patch.lower():
                    issues.append(f"📦 Potentially vulnerable package: `{pkg_name}`")
        
        return issues
