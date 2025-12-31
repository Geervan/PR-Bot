from typing import Any, Dict, List, Tuple
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
    
    # Security patterns with severity levels (Critical=50, High=35, Medium=20)
    SECURITY_PATTERNS = {
        'critical': {
            'command_injection': (50, [
                r'eval\s*\([^)]*\+',           # eval with concatenation
                r'eval\s*\(\s*[a-zA-Z_]',      # eval with variable
                r'exec\s*\([^)]*\+',           # exec with concatenation
                r'os\.system\s*\([^)]*\+',     # os.system with concatenation
                r'subprocess\.call\s*\([^,]+shell\s*=\s*True',
            ]),
            'sql_injection': (50, [
                r'execute\s*\([^,]*\+',        # execute with concatenation
                r'execute\s*\(.*%s',           # execute with string formatting
                r'cursor\.execute\s*\([^,]+\+',
                r'f["\']SELECT.*\{',           # f-string SQL
                r'f["\']INSERT.*\{',
                r'f["\']UPDATE.*\{',
                r'f["\']DELETE.*\{',
            ]),
            'path_traversal': (50, [
                r'open\s*\([^)]*\+',           # open with concatenation
                r'open\s*\(f["\']',            # open with f-string (user input in path)
                r'os\.path\.join\s*\([^)]*\+', # path.join with concatenation
                r'file_path\s*=\s*f["\']',     # file_path from f-string
                r'with\s+open\s*\(f["\']',     # with open using f-string
            ]),
        },
        'high': {
            'xss_risk': (35, [
                r'innerHTML\s*=\s*[^"\']+\+',  # innerHTML with concatenation
                r'innerHTML\s*=.*\$\{',        # innerHTML with template literal
                r'dangerouslySetInnerHTML',
                r'document\.write\s*\([^)]*\+',
            ]),
            'hardcoded_secret': (35, [
                r'password\s*=\s*["\'][^"\']{8,}["\']',  # password with 8+ chars
                r'api[_-]?key\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
                r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'AWS[_-]?SECRET[_-]?ACCESS[_-]?KEY\s*=',
                r'PRIVATE[_-]?KEY\s*=',
            ]),
            'ssrf': (50, [
                r'requests\.(get|post|put|delete)\s*\([^)]*\+',  # requests with concat
                r'requests\.(get|post|put|delete)\s*\(f["\']',   # requests with f-string
                r'urllib\.request\.urlopen\s*\([^)]*\+',
                r'httpx\.(get|post)\s*\(f["\']',
            ]),
        },
        'high': {
            'xss_risk': (35, [
                r'innerHTML\s*=\s*[^"\']+\+',  # innerHTML with concatenation
                r'innerHTML\s*=.*\$\{',        # innerHTML with template literal
                r'dangerouslySetInnerHTML',
                r'document\.write\s*\([^)]*\+',
            ]),
            'hardcoded_secret': (35, [
                r'password\s*=\s*["\'][^"\']{8,}["\']',  # password with 8+ chars
                r'api[_-]?key\s*=\s*["\'][A-Za-z0-9_\-]{20,}["\']',
                r'secret[_-]?key\s*=\s*["\'][^"\']+["\']',
                r'AWS[_-]?SECRET[_-]?ACCESS[_-]?KEY\s*=',
                r'PRIVATE[_-]?KEY\s*=',
            ]),
            'open_redirect': (35, [
                r'redirect\s*\([^)]*\+',           # redirect with concatenation
                r'redirect\s*\(.*request\.',       # redirect with request param
                r'HttpResponseRedirect\s*\([^)]*\+',
                r'res\.redirect\s*\([^)]*\+',      # Express.js
            ]),
            'template_injection': (35, [
                r'render_template_string\s*\(',    # Flask SSTI
                r'Template\s*\([^)]*\+',           # Jinja2 with concat
                r'\.render\s*\([^)]*\+',           # Generic template render
            ]),
        },
        'medium': {
            'insecure_crypto': (20, [
                r'md5\s*\(',
                r'sha1\s*\(',
                r'DES\s*\(',
                r'random\.random\s*\(\)',
            ]),
            'insecure_deserialization': (20, [
                r'pickle\.loads?\s*\(',
                r'yaml\.load\s*\([^)]*\)',     # yaml.load without safe_load
            ]),
            'nosql_injection': (20, [
                r'\$where\s*:',                # MongoDB $where
                r'\.find\s*\(\s*\{[^}]*\$',    # MongoDB operators from input
            ]),
            'weak_jwt': (20, [
                r'algorithm\s*=\s*["\']none["\']',   # JWT alg:none
                r'verify\s*=\s*False',               # JWT verify disabled
            ]),
        },
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
            
            # 6. Security pattern detection in code (with severity-based scoring)
            patterns_found = self._check_security_patterns(patch, filename)
            for issue_score, issue_text in patterns_found:
                score += issue_score
                security_issues.append(issue_text)
            
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
    
    def _check_security_patterns(self, patch: str, filename: str) -> List[Tuple[int, str]]:
        """Scan code for security issues. Returns list of (score, issue_description)."""
        issues = []
        
        if not patch:
            return issues
        
        # Only check added lines (start with +)
        added_lines = [line for line in patch.split('\n') if line.startswith('+')]
        added_code = '\n'.join(added_lines)
        
        issue_labels = {
            'command_injection': '🔴 [Critical] Command Injection',
            'sql_injection': '🔴 [Critical] SQL Injection',
            'path_traversal': '🔴 [Critical] Path Traversal',
            'ssrf': '🔴 [Critical] Server-Side Request Forgery (SSRF)',
            'xss_risk': '🟠 [High] XSS Vulnerability',
            'hardcoded_secret': '🟠 [High] Hardcoded Secret',
            'open_redirect': '🟠 [High] Open Redirect',
            'template_injection': '🟠 [High] Template Injection (SSTI)',
            'insecure_crypto': '🟡 [Medium] Insecure Cryptography',
            'insecure_deserialization': '🟡 [Medium] Insecure Deserialization',
            'nosql_injection': '🟡 [Medium] NoSQL Injection',
            'weak_jwt': '🟡 [Medium] Weak JWT Configuration',
        }
        
        # Check all severity tiers
        for severity_tier, categories in self.SECURITY_PATTERNS.items():
            for category, (score, patterns) in categories.items():
                for pattern in patterns:
                    if re.search(pattern, added_code, re.IGNORECASE):
                        label = issue_labels.get(category, category)
                        issues.append((score, f"{label} in `{filename}`"))
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
