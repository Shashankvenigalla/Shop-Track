# ShopTrack Deployment Guide

This guide covers different deployment options for the ShopTrack application.

## 🚀 Quick Start with Docker Compose

The easiest way to deploy ShopTrack is using Docker Compose:

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Ports 8000, 8050, 5432, 6379 available

### Deployment Steps

1. **Clone and setup the project:**
```bash
git clone <repository-url>
cd ShopTrack
```

2. **Create environment file:**
```bash
cp env.example .env
# Edit .env with your configuration
```

3. **Start all services:**
```bash
docker-compose up -d
```

4. **Populate sample data:**
```bash
docker-compose exec shoptrack python scripts/sample_data.py
```

5. **Access the application:**
- API Documentation: http://localhost:8000/docs
- Dashboard: http://localhost:8050
- Health Check: http://localhost:8000/health

### Docker Compose Services

- **postgres**: PostgreSQL database
- **redis**: Redis cache and message broker
- **shoptrack**: Main application (API + Dashboard)
- **celery-worker**: Background task processing
- **celery-beat**: Scheduled task scheduler
- **nginx**: Reverse proxy (optional)

## 🐳 Manual Docker Deployment

### Build the Image
```bash
docker build -t shoptrack:latest .
```

### Run with External Services
```bash
# Start PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_DB=shop_track \
  -e POSTGRES_USER=shoptrack \
  -e POSTGRES_PASSWORD=shoptrack123 \
  -p 5432:5432 \
  postgres:13

# Start Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:6-alpine

# Start ShopTrack
docker run -d --name shoptrack \
  --link postgres:postgres \
  --link redis:redis \
  -e DATABASE_URL=postgresql://shoptrack:shoptrack123@postgres:5432/shop_track \
  -e REDIS_URL=redis://redis:6379 \
  -p 8000:8000 \
  -p 8050:8050 \
  shoptrack:latest
```

## 🖥️ Local Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Git

### Installation Steps

1. **Clone the repository:**
```bash
git clone <repository-url>
cd ShopTrack
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Setup environment:**
```bash
cp env.example .env
# Edit .env with your database and Redis credentials
```

5. **Initialize database:**
```bash
# Create database tables
python -c "from app.core.database import init_db; init_db()"
```

6. **Populate sample data:**
```bash
python scripts/sample_data.py
```

7. **Start the application:**
```bash
# Option 1: Use the startup script
python start.py

# Option 2: Start components individually
# Terminal 1: API Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Dashboard
python app/dashboard/main.py

# Terminal 3: Celery Worker
celery -A app.worker.celery worker --loglevel=info

# Terminal 4: Celery Beat
celery -A app.worker.celery beat --loglevel=info
```

## ☁️ Cloud Deployment

### AWS Deployment

#### Using AWS ECS with Fargate

1. **Create ECR repository:**
```bash
aws ecr create-repository --repository-name shoptrack
```

2. **Build and push image:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
docker build -t shoptrack .
docker tag shoptrack:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/shoptrack:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/shoptrack:latest
```

3. **Create ECS cluster and services:**
```bash
# Create cluster
aws ecs create-cluster --cluster-name shoptrack-cluster

# Create task definition and services
# (Use AWS Console or CloudFormation for this step)
```

#### Using AWS RDS and ElastiCache

1. **Create RDS PostgreSQL instance**
2. **Create ElastiCache Redis cluster**
3. **Update environment variables with RDS and ElastiCache endpoints**
4. **Deploy application to ECS or EC2**

### Google Cloud Platform

#### Using Google Cloud Run

1. **Build and push to Google Container Registry:**
```bash
docker build -t gcr.io/<project-id>/shoptrack .
docker push gcr.io/<project-id>/shoptrack
```

2. **Deploy to Cloud Run:**
```bash
gcloud run deploy shoptrack \
  --image gcr.io/<project-id>/shoptrack \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure Deployment

#### Using Azure Container Instances

1. **Build and push to Azure Container Registry:**
```bash
az acr build --registry <registry-name> --image shoptrack .
```

2. **Deploy to Container Instances:**
```bash
az container create \
  --resource-group <resource-group> \
  --name shoptrack \
  --image <registry-name>.azurecr.io/shoptrack:latest \
  --ports 8000 8050 \
  --environment-variables \
    DATABASE_URL=<database-url> \
    REDIS_URL=<redis-url>
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@host:port/database
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://host:port
REDIS_DB=0

# Application
DEBUG=False
SECRET_KEY=your-secret-key-here
API_V1_STR=/api/v1

# ML Settings
ML_MODEL_PATH=models/rush_predictor.pkl
ML_UPDATE_INTERVAL=3600
PREDICTION_HORIZON=24

# Alert Settings
ALERT_THRESHOLD=0.7
LOW_STOCK_THRESHOLD=10
RUSH_PREDICTION_THRESHOLD=0.8

# Celery
CELERY_BROKER_URL=redis://host:port/1
CELERY_RESULT_BACKEND=redis://host:port/2

# Dashboard
DASHBOARD_PORT=8050
DASHBOARD_HOST=0.0.0.0
```

### Production Configuration

For production deployment:

1. **Set DEBUG=False**
2. **Use strong SECRET_KEY**
3. **Configure proper database credentials**
4. **Set up SSL/TLS certificates**
5. **Configure logging to external service**
6. **Set up monitoring and alerting**

## 📊 Monitoring and Logging

### Health Checks

- **API Health**: `GET /health`
- **Database**: Connection pool status
- **Redis**: Connection status
- **ML Model**: Model availability

### Logging

ShopTrack uses structured logging with JSON format:

```python
import structlog

logger = structlog.get_logger()
logger.info("Application started", version="1.0.0")
```

### Metrics

Key metrics to monitor:

- **Sales per hour/day**
- **Inventory turnover rate**
- **ML model accuracy**
- **API response times**
- **Database connection pool usage**
- **Redis memory usage**

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Use HTTPS/TLS for all communications
- [ ] Implement proper authentication and authorization
- [ ] Use environment variables for sensitive data
- [ ] Regular security updates for dependencies
- [ ] Database connection encryption
- [ ] Input validation and sanitization
- [ ] Rate limiting on API endpoints
- [ ] Regular backups
- [ ] Monitoring for suspicious activities

### Network Security

- **Firewall rules**: Only expose necessary ports
- **VPC**: Use private subnets for databases
- **Security groups**: Restrict access to services
- **Load balancer**: Use HTTPS termination

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL format
   - Verify network connectivity
   - Check database credentials

2. **Redis Connection Errors**
   - Verify REDIS_URL format
   - Check Redis server status
   - Verify network connectivity

3. **ML Model Issues**
   - Check model file exists
   - Verify sufficient training data
   - Check model version compatibility

4. **Dashboard Not Loading**
   - Check API server is running
   - Verify CORS settings
   - Check network connectivity

### Logs and Debugging

```bash
# View application logs
docker-compose logs shoptrack

# View Celery worker logs
docker-compose logs celery-worker

# View database logs
docker-compose logs postgres

# View Redis logs
docker-compose logs redis
```

### Performance Tuning

1. **Database Optimization**
   - Add appropriate indexes
   - Optimize queries
   - Configure connection pooling

2. **Redis Optimization**
   - Configure memory limits
   - Set appropriate TTL values
   - Monitor memory usage

3. **Application Optimization**
   - Enable caching
   - Optimize ML model inference
   - Configure worker concurrency

## 📈 Scaling

### Horizontal Scaling

1. **API Servers**: Deploy multiple instances behind load balancer
2. **Celery Workers**: Scale based on queue length
3. **Database**: Use read replicas for reporting
4. **Redis**: Use Redis Cluster for high availability

### Vertical Scaling

1. **Increase CPU/Memory** for application servers
2. **Optimize database** configuration
3. **Use faster storage** for ML models
4. **Increase Redis memory** allocation

## 🔄 Backup and Recovery

### Database Backup

```bash
# Create backup
pg_dump -h localhost -U shoptrack shop_track > backup.sql

# Restore backup
psql -h localhost -U shoptrack shop_track < backup.sql
```

### Automated Backups

Set up automated backups using:

- **AWS RDS**: Automated backups
- **Google Cloud SQL**: Automated backups
- **Azure Database**: Automated backups
- **Custom scripts**: Cron jobs for manual deployments

### Disaster Recovery

1. **Regular backups** of database and ML models
2. **Cross-region replication** for critical data
3. **Documented recovery procedures**
4. **Regular disaster recovery testing**

## 📞 Support

For deployment issues:

1. Check the troubleshooting section
2. Review application logs
3. Verify configuration settings
4. Test with sample data
5. Contact support team

## 🎯 Next Steps

After successful deployment:

1. **Populate with real data**
2. **Configure alerts and notifications**
3. **Set up monitoring dashboards**
4. **Train ML models with historical data**
5. **Integrate with existing POS systems**
6. **Set up automated reporting** 