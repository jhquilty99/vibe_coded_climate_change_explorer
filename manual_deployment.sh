export HETZNER_USER=root
export HETZNER_PORT=22
export HETZNER_HOST=188.245.105.237
export APP_DIR=/opt/vibe-coded-climate-change-explorer

rsync -avz --delete \
    -e "ssh -p $HETZNER_PORT -i ~/.ssh/hetzner_cloud" \
    --exclude='.git' \
    --exclude='.github' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='.mypy_cache' \
    --exclude='.ruff_cache' \
    --exclude='htmlcov' \
    --exclude='.coverage' \
    --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='*.egg-info' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='*.grib' \
    ./ $HETZNER_USER@$HETZNER_HOST:$APP_DIR/ 

ssh -p $HETZNER_PORT $HETZNER_USER@$HETZNER_HOST -i ~/.ssh/hetzner_cloud "
    cd $APP_DIR

    # Stop existing containers
    docker ps -aq | xargs docker stop | xargs docker rm

    # Build and start the application
    sudo docker compose -f deployment/docker-compose.prod.yml up --build -d
"

ssh -p $HETZNER_PORT $HETZNER_USER@$HETZNER_HOST -i ~/.ssh/hetzner_cloud "
    curl -f http://localhost:8000/health || exit 1
    echo 'Health check passed!'
    echo 'Local eployment completed successfully!'
"

curl -f http://188.245.105.237:8000/health || exit 1
echo 'Health check passed!'
echo 'Remote deployment completed successfully!'