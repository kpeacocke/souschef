# Security Headers Deployment Guide

**Purpose:** This guide explains how to configure security headers for SousChef when deploying with a reverse proxy (nginx, Apache, or cloud CDN). Security headers protect against common web vulnerabilities like XSS, clickjacking, and MIME type sniffing.

---

## Overview

SousChef includes a Streamlit UI (`souschef/ui/app.py`) that should be protected with security headers when deployed to production. Since Streamlit doesn't support custom HTTP headers directly, headers must be configured at the reverse proxy or CDN level.

### Required Headers

| Header | Value | Purpose |
|--------|-------|---------|
| X-Frame-Options | DENY | Prevents clickjacking attacks by disallowing iframe embedding |
| X-Content-Type-Options | nosniff | Prevents MIME type sniffing, forces declared content types |
| Content-Security-Policy | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'; font-src 'self' data:` | Restricts resource loading to prevent XSS |
| Strict-Transport-Security | max-age=31536000; includeSubDomains  | Forces HTTPS connections for 1 year |
| X-XSS-Protection | 1; mode=block | Legacy XSS filter (for older browsers) |
| Referrer-Policy | strict-origin-when-cross-origin | Controls referrer information leakage |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | Restricts browser features |

---

## Deployment Options

### Option 1: nginx Reverse Proxy (Recommended)

**Why nginx?** Lightweight, high-performance, excellent for reverse proxying Streamlit applications.

#### Configuration

Create `/etc/nginx/sites-available/souschef`:

```nginx
server {
    listen 443 ssl http2;
    server_name souschef.example.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/souschef.crt;
    ssl_certificate_key /etc/ssl/private/souschef.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
    
    # HSTS (Strict-Transport-Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Content Security Policy (CSP)
    # Note: Streamlit requires 'unsafe-inline' and 'unsafe-eval' for JavaScript
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; font-src 'self' data:; frame-ancestors 'none'" always;

    # Proxy to Streamlit
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        
        # WebSocket support for Streamlit
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK";
        add_header Content-Type text/plain;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name souschef.example.com;
    return 301 https://$server_name$request_uri;
}
```

#### Enable Configuration

```bash
# Link configuration
sudo ln -s /etc/nginx/sites-available/souschef /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

### Option 2: Apache Reverse Proxy

**Why Apache?** If you're already running Apache for other services, good integration with existing infrastructure.

#### Configuration

Enable required Apache modules:

```bash
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel  # For WebSocket support
sudo a2enmod headers
sudo a2enmod ssl
```

Create `/etc/apache2/sites-available/souschef.conf`:

```apache
<VirtualHost *:443>
    ServerName souschef.example.com
    
    # SSL Configuration
    SSLEngine on
    SSLCertificateFile /etc/ssl/certs/souschef.crt
    SSLCertificateKeyFile /etc/ssl/private/souschef.key
    SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite HIGH:!aNULL:!MD5
    SSLHonorCipherOrder on

    # Security Headers
    Header always set X-Frame-Options "DENY"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    Header always set Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; font-src 'self' data:; frame-ancestors 'none'"

    # Proxy Configuration
    ProxyPreserveHost On
    ProxyPass "/" "http://localhost:8501/"
    ProxyPassReverse "/" "http://localhost:8501/"

    # WebSocket support
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} =websocket [NC]
    RewriteRule /(.*)           ws://localhost:8501/$1 [P,L]

    # Logging
    ErrorLog ${APACHE_LOG_DIR}/souschef-error.log
    CustomLog ${APACHE_LOG_DIR}/souschef-access.log combined
</VirtualHost>

# HTTP to HTTPS redirect
<VirtualHost *:80>
    ServerName souschef.example.com
    Redirect permanent / https://souschef.example.com/
</VirtualHost>
```

#### Enable Configuration

```bash
# Enable site
sudo a2ensite souschef

# Test configuration
sudo apache2ctl configtest

# Reload Apache
sudo systemctl reload apache2
```

---

### Option 3: Docker with nginx Sidecar

**Why Docker?** Consistent deployment across environments, easy to version control infrastructure.

#### docker-compose.yml

```yaml
version: '3.8'

services:
  souschef:
    build: .
    image: souschef:latest
    container_name: souschef-app
    ports:
      - "8501:8501"
    environment:
      - SOUSCHEF_DEBUG=0
      - SOUSCHEF_DB_HOST=postgres
    networks:
      - souschef-net
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: souschef-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/certs:ro
    depends_on:
      - souschef
    networks:
      - souschef-net
    restart: unless-stopped

networks:
  souschef-net:
    driver: bridge
```

#### nginx.conf (for Docker)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream souschef {
        server souschef-app:8501;
    }

    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/ssl/certs/cert.pem;
        ssl_certificate_key /etc/ssl/certs/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;

        # Security Headers (see Option 1 for full list)
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; font-src 'self' data:; frame-ancestors 'none'" always;

        location / {
            proxy_pass http://souschef;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }
    }
}
```

---

### Option 4: Cloud CDN (AWS CloudFront, Cloudflare, Azure CDN)

**Why CDN?** Global distribution, DDoS protection, managed SSL certificates.

#### AWS CloudFront Example

```javascript
// CloudFront Distribution (Terraform)
resource "aws_cloudfront_distribution" "souschef" {
  enabled = true
  
  origin {
    domain_name = "souschef-alb.us-east-1.elb.amazonaws.com"
    origin_id   = "souschef-origin"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "souschef-origin"
    
    forwarded_values {
      query_string = true
      headers = ["Host", "Origin"]
      
      cookies {
        forward = "all"
      }
    }
    
    viewer_protocol_policy = "redirect-to-https"
  }

  # Custom Response Headers (Lambda@Edge function)
  lambda_function_association {
    event_type   = "origin-response"
    lambda_arn   = aws_lambda_function.security_headers.qualified_arn
    include_body = false
  }

  viewer_certificate {
    acm_certificate_arn = aws_acm_certificate.souschef.arn
    ssl_support_method  = "sni-only"
  }
}

// Lambda@Edge for Security Headers
resource "aws_lambda_function" "security_headers" {
  function_name = "souschef-security-headers"
  handler       = "index.handler"
  runtime       = "nodejs18.x"
  role          = aws_iam_role.lambda_edge.arn
  publish       = true

  filename = "security_headers.zip"
}
```

#### Lambda@Edge Function (security_headers/index.js)

```javascript
exports.handler = async (event) => {
    const response = event.Records[0].cf.response;
    const headers = response.headers;

    headers['x-frame-options'] = [{ key: 'X-Frame-Options', value: 'DENY' }];
    headers['x-content-type-options'] = [{ key: 'X-Content-Type-Options', value: 'nosniff' }];
    headers['x-xss-protection'] = [{ key: 'X-XSS-Protection', value: '1; mode=block' }];
    headers['strict-transport-security'] = [{ 
        key: 'Strict-Transport-Security', 
        value: 'max-age=31536000; includeSubDomains' 
    }];
    headers['content-security-policy'] = [{ 
        key: 'Content-Security-Policy', 
        value: "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' ws: wss:; font-src 'self' data:; frame-ancestors 'none'"
    }];
    headers['referrer-policy'] = [{ 
        key: 'Referrer-Policy', 
        value: 'strict-origin-when-cross-origin' 
    }];

    return response;
};
```

---

## Verification

### 1. Test Security Headers Locally

```bash
# Test nginx configuration
curl -I https://souschef.example.com | grep -E "(X-Frame-Options|X-Content-Type-Options|Strict-Transport-Security)"

# Expected output:
# X-Frame-Options: DENY  
# X-Content-Type-Options: nosniff
# Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 2. Online Security Header Scanners

Use automated tools to verify header configuration:

**SecurityHeaders.com:**
```bash
https://securityheaders.com/?q=https://souschef.example.com
```
Target: **A+ rating**

**Mozilla Observatory:**
```bash
https://observatory.mozilla.org/analyze/souschef.example.com
```
Target: **A rating** (90+/100)

### 3. Manual Browser Testing

Open browser DevTools (F12) → Network tab → Reload page → Check response headers:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

---

## Troubleshooting

### Issue: Streamlit App Doesn't Load

**Symptom:** Blank page, console errors: "Refused to execute inline script"

**Cause:** CSP header too restrictive, Streamlit requires `'unsafe-inline'` and `'unsafe-eval'`

**Fix:** Update CSP to allow inline scripts:
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ...
```

### Issue: WebSocket Connection Fails

**Symptom:** "WebSocket connection failed" in browser console

**Cause:** nginx not configured for WebSocket proxying

**Fix:** Add WebSocket headers to nginx config:
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

### Issue: Headers Not Applied to Static Files

**Symptom:** Security scanner reports missing headers on CSS/JS files

**Cause:** Headers only added to HTML responses

**Fix:** Add `always` directive to nginx headers:
```nginx
add_header X-Frame-Options "DENY" always;
```

---

## Security Best Practices

### 1. SSL/TLS Configuration

- **Use TLS 1.2+ only**: Disable SSLv3, TLS 1.0, TLS 1.1
- **Strong cipher suites**: Prefer modern ciphers (AES-GCM, ChaCha20)
- **Certificate management**: Use Let's Encrypt or corporate PKI
- **HSTS preload**: Consider adding your domain to HSTS preload list

### 2. CSP Gradual Rollout

Start with report-only mode to avoid breaking functionality:

```nginx
# Phase 1: Report violations without blocking
add_header Content-Security-Policy-Report-Only "default-src 'self'; report-uri /csp-report" always;

# Phase 2: After reviewing reports, enforce policy
add_header Content-Security-Policy "default-src 'self'; ..." always;
```

### 3. Monitoring

Log and monitor security header violations:

```nginx
# nginx: Log CSP violations
location /csp-report {
    access_log /var/log/nginx/csp-violations.log;
    return 204;
}
```

---

## Compliance Mapping

| Requirement | Headers | Standard |
|-------------|---------|----------|
| Prevent clickjacking | X-Frame-Options: DENY | OWASP A01, CWE-1021 |
| Prevent MIME sniffing | X-Content-Type-Options: nosniff | OWASP A04, CWE-79 |
| Enforce HTTPS | Strict-Transport-Security | OWASP A02, CWE-319 |
| Restrict content sources | Content-Security-Policy | OWASP A03, CWE-79 |
| Limit browser features | Permissions-Policy | Privacy regulations |

---

## References

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [MDN Web Security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [nginx Security Headers Guide](https://www.nginx.com/blog/improving-security-application-security-nginx-plus/)
- [Streamlit Deployment Best Practices](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)
- [Content Security Policy Reference](https://content-security-policy.com/)

---

## Maintenance Checklist

**Quarterly Review:**
- [ ] Run SecurityHeaders.com scan
- [ ] Review CSP violation logs
- [ ] Update SSL certificates (if not automated)
- [ ] Test WebSocket connectivity
- [ ] Verify HSTS is active
- [ ] Check for new security header recommendations

**After Major Streamlit Upgrades:**
- [ ] Test CSP compatibility
- [ ] Verify WebSocket connections
- [ ] Check browser console for errors
- [ ] Update CSP if Streamlit adds new resource requirements
