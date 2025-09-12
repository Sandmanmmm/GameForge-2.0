#!/bin/bash
echo "Deploying Elasticsearch Infrastructure"

# Start the services
docker-compose -f docker-compose.elasticsearch.yml up -d

echo "Elasticsearch deployment complete!"
echo "Access points:"
echo "  - Elasticsearch: http://localhost:9200"
echo "  - Kibana: http://localhost:5601"
echo "  - Logstash: http://localhost:9600"
