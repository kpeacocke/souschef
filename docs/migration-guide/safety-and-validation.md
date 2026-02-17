# Production Safety & Validation

## Why This Matters

Ansible and Chef automation affects **production systems** - infrastructure, applications, databases, and ongoing operations. A bad conversion can cause outages, data loss, or security vulnerabilities. SousChef provides tools to validate migrations thoroughly before production deployment.

This guide explains how to:

- Verify generated Ansible is functionally equivalent to Chef
- Test conversions in safe environments
- Build confidence before production rollout
- Plan rollback strategies
- Execute phased migrations with minimal risk

## The Safety Pyramid

```
                  /\
                 /  \ Production Deploy (100% confidence)
                /────\
               /      \ Production Pilot (95% confidence)
              /────────\
             /          \ Staging Validation (90% confidence)
            /────────────\
           /              \ Development Testing (80% confidence)
          /────────────────\
         /                  \ Static Analysis (baseline)
        /────────────────────\
```

Work your way up the pyramid. Never skip steps.

## Phase 1: Static Analysis (Baseline)

### Validate Conversion Accuracy

**Use SousChef's validation tools** to check the conversion quality:

```
Validate the conversion from cookbook-name
```

Your AI assistant will use the `validate_conversion` tool to:
- Compare Chef resources vs generated Ansible tasks
- Identify missing resources or incorrect mappings
- Flag complex Chef patterns that need manual review
- Highlight security-sensitive resources (users, SSH keys, credentials)

**Manual Review Checklist:**

- [ ] All Chef resources have corresponding Ansible tasks
- [ ] Guards (`only_if`, `not_if`) properly converted to `when` conditions
- [ ] Resource notifications mapped to handlers
- [ ] File/template permissions preserved
- [ ] Service management actions correct (start, enable, restart)
- [ ] Package version specifications maintained
- [ ] Complex bash/ruby scripts reviewed for shell escaping

### Compare Side-by-Side

**For critical resources**, manually compare Chef and Ansible:

```ruby
# Chef original
package 'nginx' do
  version '1.18.0-6ubuntu14.4'
  action :install
  notifies :restart, 'service[nginx]'
end
```

```yaml
# Generated Ansible
- name: Install nginx
  ansible.builtin.package:
    name: nginx
    state: present
    version: 1.18.0-6ubuntu14.4
  notify: restart nginx

handlers:
  - name: restart nginx
    ansible.builtin.service:
      name: nginx
      state: restarted
```

**Key validation points:**
- Package lock versions matched exactly (especially for applications)
- Notification triggers are preserved
- Service state expectations align
- File paths are correct for target platform

### Security Review

**Critical for production systems:**

- [ ] Secrets management strategy defined (Ansible Vault vs Chef data bags)
- [ ] File permissions match Chef exactly (especially for keys, configs)
- [ ] User/group creation preserves UIDs/GIDs where necessary
- [ ] SSH key deployments are secure
- [ ] Application credentials handled correctly
- [ ] No secrets leaked in plain text playbooks

**Use SousChef security scanning:**
```
Check the generated playbooks for security issues
```

## Phase 2: Development Testing (80% Confidence)

### Test in Disposable Environment

**Create identical infrastructure** for testing:

1. **Use Infrastructure-as-Code** (Terraform, CloudFormation, Vagrant):
   ```hcl
   # Terraform example
   resource "aws_instance" "test" {
     ami           = "ami-ubuntu-22.04"  # Match production
     instance_type = "t3.medium"         # Match production
     tags = {
       Environment = "ansible-migration-test"
     }
   }
   ```

2. **Snapshot baseline state** (pre-Chef run):
   - System packages and versions
   - Running services
   - File checksums (especially configs)
   - Network ports
   - Application functionality

3. **Run Chef cookbook** to establish baseline:
   ```bash
   chef-client --local-mode --runlist 'recipe[cookbook-name]'
   ```

4. **Verify baseline functionality**:
   - Applications respond correctly
   - Services are running
   - Configurations are correct
   - Day-2 operations work (backups, monitoring, log shipping)

5. **Rebuild fresh environment** (destroy and recreate)

6. **Run Ansible playbook**:
   ```bash
   ansible-playbook -i inventory playbook-name.yml -vv
   ```

7. **Compare states** (Ansible vs Chef):
   ```bash
   # Package comparison
   diff <(chef-state-packages) <(ansible-state-packages)

   # File comparison
   diff -r /etc/app/chef-configs /etc/app/ansible-configs

   # Service comparison
   systemctl status service-name  # Same on both?
   ```

### Automated Testing with InSpec/Testlnfra

**Convert Chef InSpec tests to Ansible validation:**

```
Generate InSpec tests from the recipe at recipes/default.rb
```

**Example InSpec test:**
```ruby
describe package('nginx') do
  it { should be_installed }
  its('version') { should match /^1\.18/ }
end

describe service('nginx') do
  it { should be_running }
  it { should be_enabled }
end

describe file('/etc/nginx/nginx.conf') do
  it { should exist }
  its('mode') { should cmp '0644' }
  its('owner') { should eq 'root' }
end

describe port(80) do
  it { should be_listening }
end
```

**Run against both Chef and Ansible results:**
```bash
# Chef-managed system
inspec exec tests/nginx-test.rb -t ssh://chef-node

# Ansible-managed system
inspec exec tests/nginx-test.rb -t ssh://ansible-node

# Compare outputs
```

**Ansible assert tasks** (alternative to InSpec):
```yaml
- name: Verify nginx is installed
  ansible.builtin.package_facts:

- name: Assert nginx version
  ansible.builtin.assert:
    that:
      - "'nginx' in ansible_facts.packages"
      - "ansible_facts.packages.nginx[0].version is match('^1.18')"
```

### Application-Level Testing

**For application cookbooks**, functional tests are critical:

**Web applications:**
```bash
# Test endpoints
curl -f http://test-server/health || exit 1
curl -f http://test-server/api/v1/status || exit 1

# Test authentication
curl -u testuser:password http://test-server/private || exit 1

# Test database connectivity
curl -f http://test-server/api/v1/db-check || exit 1
```

**Databases:**
```bash
# Test connectivity
psql -h test-db -U appuser -c "SELECT 1" || exit 1

# Test permissions
psql -h test-db -U appuser -c "CREATE TABLE test_table (id INT)" || exit 1

# Test backup procedures
pg_dump -h test-db -U appuser appdb > /tmp/test-backup.sql || exit 1
```

**Message queues:**
```bash
# Test RabbitMQ
rabbitmqctl status || exit 1
rabbitmqadmin list queues || exit 1

# Test Kafka
kafka-topics --list --bootstrap-server test-kafka:9092 || exit 1
```

### Day-2 Operations Testing

**Critical for production confidence:**

**Backup and restore:**
```bash
# Test backup creation
ansible-playbook playbooks/backup.yml

# Verify backup files exist
ls -lh /backup/appdb-$(date +%Y%m%d)* || exit 1

# Test restore procedure
ansible-playbook playbooks/restore.yml -e backup_file=/backup/appdb-20260217.sql
```

**Scaling operations:**
```bash
# Test scale-up playbook
ansible-playbook playbooks/scale-up.yml -e target_instances=5

# Test scale-down playbook
ansible-playbook playbooks/scale-down.yml -e target_instances=3
```

**Configuration updates:**
```bash
# Test config change deployment
ansible-playbook playbooks/update-config.yml -e new_workers=8

# Verify change applied without downtime
curl -f http://test-server/health || exit 1
```

**Monitoring and logging:**
```bash
# Test monitoring agent deployment
ansible-playbook playbooks/monitoring.yml

# Verify metrics collection
curl -f http://monitoring-server/api/v1/query?query=up || exit 1

# Test log shipping
tail -f /var/log/app/app.log  # Verify logs appear in aggregator
```

## Phase 3: Staging Validation (90% Confidence)

### Production-Like Environment

**Staging should mirror production:**
- Same OS versions and patches
- Same network topology (subnets, firewalls)
- Same data volumes (even if sanitized/synthetic)
- Same integrations (APIs, databases, message queues)
- Same monitoring and logging
- Same backup procedures

### Full Integration Testing

**Run complete workflows** that exercise the system:

**E-commerce example:**
1. User registration
2. Product browsing
3. Add to cart
4. Checkout process
5. Payment processing (test mode)
6. Order fulfilment
7. Email notifications

**API service example:**
1. Authentication via OAuth
2. CRUD operations on all resources
3. Pagination and filtering
4. Rate limiting behaviour
5. Error handling (4xx, 5xx responses)
6. Batch operations
7. Webhook delivery

### Load Testing

**Verify performance under Ansible-managed infrastructure:**

```bash
# Load test with Apache Bench
ab -n 10000 -c 100 http://staging-server/

# Load test with k6
k6 run --vus 100 --duration 30s load-test.js

# Database load test
pgbench -h staging-db -U appuser -c 50 -j 4 -T 300 appdb
```

**Compare metrics:**
- Chef-managed: X req/sec, Y ms p95 latency
- Ansible-managed: Should match or exceed

### Security Validation

**Run security scans on Ansible-managed systems:**

```bash
# Vulnerability scanning
nmap -sV -A staging-server

# Configuration hardening check
ansible-playbook --check playbooks/hardening.yml

# Compliance scanning (CIS benchmarks)
inspec exec profiles/cis-ubuntu-22.04 -t ssh://staging-server
```

### Disaster Recovery Testing

**Test failure scenarios:**

**Service failure:**
```bash
# Kill service
sudo systemctl stop nginx

# Verify monitoring alerts
# Verify Ansible remediation (if automated)

# Manual remediation
ansible-playbook playbooks/recover-nginx.yml
```

**Database failure:**
```bash
# Simulate database corruption
# Run restore from backup
ansible-playbook playbooks/restore-database.yml

# Verify data integrity
# Verify application functionality
```

**Full system failure:**
```bash
# Destroy staging infrastructure
terraform destroy -auto-approve

# Rebuild from scratch with Ansible
terraform apply -auto-approve
ansible-playbook site.yml

# Verify complete system functionality
smoke-test.sh
```

## Phase 4: Production Pilot (95% Confidence)

### Canary Deployment

**Deploy to a subset of production infrastructure first:**

**Strategy 1: Geographic rollout**
```
Week 1: Deploy to APAC region (lowest traffic)
Week 2: Deploy to EMEA region
Week 3: Deploy to Americas region (highest traffic)
```

**Strategy 2: Service-based rollout**
```
Week 1: Deploy to internal web services
Week 2: Deploy to API gateway
Week 3: Deploy to customer-facing web servers
```

**Strategy 3: Blue-green deployment**
```
1. Build new "green" environment with Ansible
2. Route 10% traffic to green
3. Monitor for 48 hours
4. Increase to 50% traffic
5. Monitor for 1 week
6. Complete cutover to green
7. Decommission "blue" (Chef-managed)
```

### Monitoring During Pilot

**Critical metrics to watch:**

**System metrics:**
- CPU, memory, disk usage (should match Chef baseline)
- Network traffic patterns
- Service response times
- Error rates

**Application metrics:**
- Request rates and latency (p50, p95, p99)
- Database query performance
- Cache hit rates
- Background job queue lengths
- Application-specific KPIs

**Business metrics:**
- Transaction success rates
- User engagement metrics
- Revenue impact (for e-commerce)
- SLA compliance

**Set up alerts:**
```yaml
# Prometheus alert example
- alert: AnsibleMigrationPerformanceRegression
  expr: http_request_duration_p95 > 200
  for: 10m
  labels:
    severity: critical
  annotations:
    summary: "Performance regression detected in Ansible-managed infrastructure"
```

### Rollback Plan

**Always have a rollback strategy before piloting:**

**Quick rollback (< 5 minutes):**
```bash
# Switch traffic back to Chef-managed infrastructure
# Update load balancer / DNS
terraform apply -var "active_pool=chef-pool"
```

**Full rollback (< 30 minutes):**
```bash
# Revert infrastructure changes
terraform workspace select chef-managed
terraform apply

# Re-run Chef
chef-client --local-mode --runlist 'recipe[cookbook-name]'

# Verify functionality
smoke-test.sh
```

**Document rollback triggers:**
- Error rate > X% increase
- Latency > Y ms increase
- Failed health checks
- Database connection issues
- Customer complaints > Z threshold

## Phase 5: Production Deploy (100% Confidence)

### Final Cutover

**After successful pilot**, complete the migration:

1. **Scheduled maintenance window** (if downtime required)
2. **Final Ansible deployment** to remaining infrastructure
3. **Verification** of all systems
4. **Decommission Chef infrastructure** (after retention period)

### Post-Deployment Monitoring

**Monitor for 30 days post-cutover:**
- Same metrics as pilot phase
- Watch for delayed issues (memory leaks, log rotation, backup failures)
- Validate day-2 operations (patches, config updates, scaling events)

### Documentation Update

**Update operational runbooks:**
- Replace Chef commands with Ansible equivalents
- Update disaster recovery procedures
- Update onboarding docs for new ops team members
- Document new CI/CD pipeline integration

## Troubleshooting Common Issues

### "Ansible generates different file than Chef"

**Cause**: Template variables, file paths, or permissions differ.

**Solution**:
1. Compare files byte-by-byte: `diff -u chef-file ansible-file`
2. Check template variable mapping: `parse_template path/to/template.erb`
3. Verify file permissions: `ls -la chef-file ansible-file`
4. Check for Chef-specific Ruby code in templates

### "Service fails to start under Ansible"

**Cause**: Dependencies not satisfied, configs incorrect, or timing issues.

**Solution**:
1. Check service dependencies: `systemctl list-dependencies service-name`
2. Review systemd logs: `journalctl -u service-name -n 50`
3. Validate configuration syntax: `service-name-binary check-config`
4. Add pre-start validation tasks in Ansible
5. Check for race conditions (services starting before dependencies ready)

### "Application breaks after Ansible deployment"

**Cause**: Environment variables, application configs, or runtime dependencies differ.

**Solution**:
1. Compare environment variables: `printenv` on both systems
2. Check application logs for specific errors
3. Verify database connection strings
4. Validate API endpoints and URLs
5. Check for hard-coded paths that differ between environments
6. Review application-specific Chef resources that may need special handling

### "Performance degradation after migration"

**Cause**: Configuration tuning, resource limits, or caching differ.

**Solution**:
1. Compare system resource limits: `ulimit -a`
2. Check application tuning (worker processes, thread pools, connection pool sizes)
3. Verify caching configuration (Redis, Memcached)
4. Review kernel parameters: `sysctl -a`
5. Check for missing performance optimizations from Chef
6. Profile application under load to find bottlenecks

## Best Practices Summary

✅ **DO:**
- Test in disposable environments first
- Compare Chef and Ansible results side-by-side
- Use automated testing (InSpec, assert tasks)
- Test day-2 operations thoroughly
- Test application-level functionality, not just infrastructure
- Deploy in phases (dev → staging → pilot → production)
- Monitor extensively during pilot
- Have a documented rollback plan
- Validate backups and disaster recovery

❌ **DON'T:**
- Skip testing phases
- Deploy directly to production
- Ignore security validation
- Assume generated Ansible is perfect
- Rush the migration timeline
- Forget about application dependencies
- Ignore monitoring and logging
- Deploy without a rollback plan
- Forget day-2 operations

## Additional Resources

- [SousChef Validation Tools](../user-guide/mcp-tools.md#validation-testing)
- [Migration Guide: Advanced Workflows](advanced-workflows.md)
- [SECURITY.md](../../SECURITY.md) - Security features and best practices
- [Ansible Testing Strategies](https://docs.ansible.com/ansible/latest/reference_appendices/test_strategies.html)
- [InSpec Documentation](https://docs.chef.io/inspec/)

## Getting Help

If you encounter migration issues:

1. Review validation tool output for specific problems
2. Compare Chef and Ansible results in detail
3. Check application logs and system logs
4. Test in isolated environment
5. Open a [GitHub issue](https://github.com/kpeacocke/souschef/issues) with:
   - Chef cookbook excerpt
   - Generated Ansible playbook
   - Observed vs expected behaviour
   - Test environment details

For security concerns, see [SECURITY.md](../../SECURITY.md).
