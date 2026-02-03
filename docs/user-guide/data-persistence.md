# Data Persistence and Storage Guide

SousChef v3.6+ includes comprehensive data persistence capabilities to store analysis history, conversion results, and generated assets across container restarts.

## Features

### Persistent Storage
- **SQLite Database**: Stores analysis results, conversion history, and metadata
- **PostgreSQL Database**: Production-grade relational database for shared deployments
- **Blob Storage**: Stores generated Ansible playbooks, roles, and supporting files
- **Cache Layer**: Automatically caches AI analysis results to save costs and time
- **Historical Tracking**: View and download past analyses and conversions

### Database Schema

The persistence layer uses SQLite or PostgreSQL with the following tables:

#### Analysis Results
- Cookbook name, version, and metadata
- Complexity ratings and effort estimates
- AI provider and model used
- Full analysis data (JSON)
- Cache keys for efficient lookups
- **Source archive reference** (v3.7+): Blob storage key for uploaded cookbook
- Timestamps

#### Conversion Results
- Output type (playbook/role/collection)
- Status (success/partial/failed)
- Files generated count
- Blob storage reference
- Full conversion data (JSON)
- Links to original analysis

### Storage Backends

#### Local Storage (Default)
Stores data in `~/.souschef/`:
- `data/souschef.db` - SQLite database
- `storage/` - Generated artefacts

```python
from souschef.storage import get_storage_manager, get_blob_storage

# Uses default local storage
storage = get_storage_manager()
blob = get_blob_storage("local")
```

#### S3-Compatible Storage
Use AWS S3, MinIO, or any S3-compatible service:

```python
from souschef.storage import get_blob_storage

# AWS S3
blob = get_blob_storage(
    backend="s3",
    bucket_name="souschef-artefacts",
    region="us-east-1"
    # access_key and secret_key from environment or explicit
)

# MinIO
blob = get_blob_storage(
    backend="s3",
    bucket_name="souschef",
    endpoint_url="http://minio:9000",
    access_key="admin",
    secret_key="password"
)
```

## Using the History Page

The History page in the UI provides comprehensive access to all past analyses and conversions.

### Analysis History
1. Navigate to **History** in the main navigation
2. Click the **Analysis History** tab
3. Filter by cookbook name (optional)
4. View detailed metrics:
   - Complexity ratings
   - Manual vs AI-assisted effort estimates
   - Time saved
   - AI provider/model used
5. Click on individual analyses to see full details and recommendations

**Source Archive Storage** (v3.7+):
- When you upload a cookbook archive (tar/zip), it's automatically stored alongside the analysis
- Stored archives enable re-conversion without re-uploading
- Archives are referenced by `cookbook_blob_key` in the database
- Future versions will enable one-click re-conversion from stored archives

### Conversion History
1. Navigate to **History** in the main navigation
2. Click the **Conversion History** tab
3. Filter by cookbook name or status
4. View conversion details:
   - Success/failure status
   - Files generated
   - Output types (playbook/role/collection)
5. Download previously generated artefacts with one click

**Automatic Archive Creation** (v3.6+):
- Conversion artefacts are automatically stored as tar/zip archives during conversion
- Both roles and repository archives are saved to blob storage
- Archives are immediately available for download from the History page
- No need to regenerate - just click to download pre-created archives

### Statistics Dashboard
View overall metrics:
- Total analyses performed
- Unique cookbooks analysed
- Total conversions and success rate
- Average time saved with AI assistance
- Total files generated

## Automated Caching

SousChef automatically caches AI analysis results to:
- **Reduce costs**: Avoid re-running expensive AI analyses
- **Improve speed**: Serve cached results instantly
- **Maintain consistency**: Same cookbook + AI settings = cached result

### Cache Invalidation
Cache is automatically invalidated when:
- Cookbook content changes (detected via content hash)
- Different AI provider or model is used
- Manual cache clear (future feature)

### Cache Keys
Cache keys are generated from:
```
SHA256(cookbook_path + ai_provider + ai_model + content_hash)
```

## Mass Analysis and Conversion

### Batch Analysis
For entire Chef estates:

1. **Prepare Archive**:
   ```bash
   # Create archive of all cookbooks
   tar czf chef_estate.tar.gz /path/to/cookbooks/*
   ```

2. **Upload to SousChef UI**:
   - Navigate to Cookbook Analysis
   - Upload the archive
   - Click "Analyse ALL Cookbooks"

3. **View Results**:
   - Results are automatically saved to database
   - Access anytime from History page
   - Download comprehensive reports

### Parallel Processing
For large estates, SousChef processes cookbooks in parallel:
- Checks cache before analysis (instant for cached cookbooks)
- Analyses new cookbooks in batches
- Saves results incrementally
- Shows progress for long-running operations

## API Usage

### Saving Analysis Results

```python
from souschef.storage import get_storage_manager

storage = get_storage_manager()

# Save analysis
analysis_id = storage.save_analysis(
    cookbook_name="nginx",
    cookbook_path="/cookbooks/nginx",
    cookbook_version="1.0.0",
    complexity="Medium",
    estimated_hours=16.0,
    estimated_hours_with_souschef=8.0,
    recommendations="Use Ansible Galaxy nginx role...",
    analysis_data={"details": "..."},
    ai_provider="anthropic",
    ai_model="claude-3-5-sonnet-20241022",
    cookbook_blob_key="cookbooks/nginx/nginx-1.0.0.tar.gz"  # Optional: v3.7+
)
```

### Retrieving Cached Results

```python
# Check for cached analysis
cached = storage.get_cached_analysis(
    "/cookbooks/nginx",
    ai_provider="anthropic",
    ai_model="claude-3-5-sonnet-20241022"
)

if cached:
    print(f"Found cached analysis from {cached.created_at}")
    print(f"Complexity: {cached.complexity}")
    print(f"Recommendations: {cached.recommendations}")
```

### Saving Conversion Results

```python
# Save conversion with blob storage reference
# Note: In UI mode (v3.6+), this happens automatically during conversion
conversion_id = storage.save_conversion(
    cookbook_name="nginx",
    output_type="role",
    status="success",
    files_generated=12,
    conversion_data={
        "parsed_result": {...},
        "roles_blob_key": "conversions/nginx/roles_20250202_123456",
        "repo_blob_key": "conversions/nginx/repo_20250202_123500",
        "timestamp": "20250202_123456"
    },
    analysis_id=analysis_id,
    blob_storage_key="conversions/nginx/roles_20250202_123456"
)
```

**Automatic Conversion Storage (UI)**:
- When you convert cookbooks in the UI, artefacts are automatically:
  1. Uploaded to blob storage as tar/zip archives
  2. Saved to database with blob storage keys
  3. Made available for download from the History page
- Both roles and repository archives are stored separately
- Archives include timestamps for version tracking

### Uploading to Blob Storage

```python
from pathlib import Path
from souschef.storage import get_blob_storage

blob = get_blob_storage("local")

# Upload directory (automatically zipped)
storage_key = blob.upload(
    Path("/tmp/nginx_role"),
    "conversions/nginx_20250202_123456"
)
print(f"Uploaded to: {storage_key}")

# Download later
blob.download(
    storage_key,
    Path("/tmp/restored_nginx_role")
)
```

## Environment Configuration

Configure storage via environment variables:

```bash
# Default local storage (no config needed)

# Default SQLite database (no config needed)

# PostgreSQL database
export SOUSCHEF_DB_BACKEND=postgres
export SOUSCHEF_DB_HOST=postgres
export SOUSCHEF_DB_PORT=5432
export SOUSCHEF_DB_NAME=souschef
export SOUSCHEF_DB_USER=souschef
export SOUSCHEF_DB_PASSWORD=souschef
export SOUSCHEF_DB_SSLMODE=disable

# For S3 storage
export SOUSCHEF_STORAGE_BACKEND=s3
export SOUSCHEF_S3_BUCKET=souschef-artefacts
export SOUSCHEF_S3_REGION=us-east-1
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret

# For MinIO
export SOUSCHEF_STORAGE_BACKEND=s3
export SOUSCHEF_S3_BUCKET=souschef
export SOUSCHEF_S3_ENDPOINT=http://minio:9000
export SOUSCHEF_S3_ACCESS_KEY=admin
export SOUSCHEF_S3_SECRET_KEY=password
```

## Docker Deployment

### Persistent Volumes

Mount volumes to persist data across container restarts:

```yaml
# docker-compose.yml
version: '3.8'

services:
  souschef-ui:
    image: souschef-ui:latest
    volumes:
      # Persist database and local storage
      - souschef-data:/tmp/.souschef/data
      - souschef-storage:/tmp/.souschef/storage
      # Optional: mount S3 credentials
      - ~/.aws:/root/.aws:ro
    environment:
      - SOUSCHEF_DB_BACKEND=sqlite
      - SOUSCHEF_STORAGE_BACKEND=local
    ports:
      - "8501:8501"

volumes:
  souschef-data:
    driver: local
  souschef-storage:
    driver: local
```

### With PostgreSQL and MinIO

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: souschef
      POSTGRES_USER: souschef
      POSTGRES_PASSWORD: souschef
    volumes:
      - postgres-data:/var/lib/postgresql/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

  souschef-ui:
    image: souschef-ui:latest
    depends_on:
      - postgres
      - minio
    environment:
      - SOUSCHEF_DB_BACKEND=postgres
      - SOUSCHEF_DB_HOST=postgres
      - SOUSCHEF_DB_PORT=5432
      - SOUSCHEF_DB_NAME=souschef
      - SOUSCHEF_DB_USER=souschef
      - SOUSCHEF_DB_PASSWORD=souschef
      - SOUSCHEF_STORAGE_BACKEND=s3
      - SOUSCHEF_S3_BUCKET=souschef
      - SOUSCHEF_S3_ENDPOINT=http://minio:9000
      - SOUSCHEF_S3_ACCESS_KEY=minioadmin
      - SOUSCHEF_S3_SECRET_KEY=minioadmin
    volumes:
      - souschef-data:/tmp/.souschef/data
      - souschef-storage:/tmp/.souschef/storage
    ports:
      - "8501:8501"

volumes:
  minio-data:
  postgres-data:
  souschef-data:
  souschef-storage:
```

## Best Practices

### 1. Regular Backups
```bash
# Backup SQLite database
cp ~/.souschef/data/souschef.db ~/backups/souschef_$(date +%Y%m%d).db

# For S3, enable versioning on the bucket
aws s3api put-bucket-versioning \
  --bucket souschef-artefacts \
  --versioning-configuration Status=Enabled
```

### 2. Cache Management
- Cache grows over time - monitor disk usage
- Cached analyses are automatically reused
- Different AI models create separate cache entries

### 3. Large Estates
- Upload cookbooks in batches if possible
- Use S3 storage for large numbers of conversions
- Enable parallel processing for faster analysis

### 4. Cost Optimization
- Caching dramatically reduces AI API costs
- Analyse similar cookbooks in the same session
- Review cached results before re-analysing

## Troubleshooting

### Database Locked Errors
SQLite may show "database is locked" under heavy concurrent use:
```python
# Configure in storage manager (future enhancement)
# For now, retry operations or use PostgreSQL backend
```

### Storage Path Errors
Ensure the storage directory is writable:
```bash
# Check permissions
ls -la ~/.souschef/
chmod 700 ~/.souschef/
```

### S3 Connection Issues
Verify credentials and connectivity:
```python
from souschef.storage import get_blob_storage

try:
    blob = get_blob_storage("s3", bucket_name="test-bucket")
    keys = blob.list_keys()
    print(f"Connected successfully, found {len(keys)} objects")
except Exception as e:
    print(f"Connection failed: {e}")
```

### Cache Not Working
Verify cache key generation:
```python
from souschef.storage import get_storage_manager

storage = get_storage_manager()
cache_key = storage.generate_cache_key(
    "/path/to/cookbook",
    ai_provider="anthropic",
    ai_model="claude-3-5-sonnet-20241022"
)
print(f"Cache key: {cache_key}")

# Check if cached entry exists
cached = storage.get_cached_analysis(
    "/path/to/cookbook",
    ai_provider="anthropic",
    ai_model="claude-3-5-sonnet-20241022"
)
print(f"Cached: {cached is not None}")
```

## Future Enhancements

Planned features for upcoming releases:

- [ ] PostgreSQL backend for multi-user deployments
- [ ] Manual cache invalidation controls
- [ ] Export/import database snapshots
- [ ] Azure Blob Storage support
- [ ] Google Cloud Storage support
- [ ] Retention policies for old analyses
- [ ] Data deduplication for similar cookbooks
- [ ] Full-text search across analysis history
- [ ] Collaborative analysis sharing

## Migration from Previous Versions

If you're upgrading from SousChef v3.5 or earlier:

1. **No migration needed**: The database is created automatically
2. **Existing data**: Previous session state data is lost (by design)
3. **New analyses**: Will be automatically persisted going forward
4. **Re-analyse**: Consider re-analysing important cookbooks to populate history

---

For more information, see:
- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](../api-reference/)
- [Docker Deployment Guide](docker-deployment.md)
