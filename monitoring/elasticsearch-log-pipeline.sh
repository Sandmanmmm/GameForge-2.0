#!/bin/bash
# ========================================================================
# Enhanced Elasticsearch Log Aggregation Pipeline
# GameForge AI Production Log Processing with ILM and Security
# ========================================================================

# Wait for Elasticsearch to be ready
echo "Waiting for Elasticsearch to be ready..."
until curl -s "elasticsearch:9200/_cluster/health" | grep -q '"status":"green\|yellow"'; do
  echo "Waiting for Elasticsearch..."
  sleep 5
done

echo "Setting up Elasticsearch log aggregation pipeline..."

# ========================================================================
# Index Lifecycle Management Policy
# ========================================================================
echo "Creating ILM policy..."
curl -X PUT "elasticsearch:9200/_ilm/policy/gameforge-logs-policy" \
  -H 'Content-Type: application/json' \
  -d '{
  "policy": {
    "phases": {
      "hot": {
        "min_age": "0ms",
        "actions": {
          "rollover": {
            "max_primary_shard_size": "50GB",
            "max_age": "1d",
            "max_docs": 10000000
          },
          "set_priority": {
            "priority": 100
          }
        }
      },
      "warm": {
        "min_age": "1d",
        "actions": {
          "set_priority": {
            "priority": 50
          },
          "allocate": {
            "number_of_replicas": 0
          },
          "forcemerge": {
            "max_num_segments": 1
          }
        }
      },
      "cold": {
        "min_age": "7d",
        "actions": {
          "set_priority": {
            "priority": 0
          },
          "allocate": {
            "number_of_replicas": 0
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}'

# ========================================================================
# Index Template for GameForge Logs
# ========================================================================
echo "Creating index template..."
curl -X PUT "elasticsearch:9200/_index_template/gameforge-logs-template" \
  -H 'Content-Type: application/json' \
  -d '{
  "index_patterns": ["gameforge-logs-*"],
  "template": {
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1,
      "index.lifecycle.name": "gameforge-logs-policy",
      "index.lifecycle.rollover_alias": "gameforge-logs",
      "index.refresh_interval": "5s",
      "index.max_result_window": 100000,
      "analysis": {
        "analyzer": {
          "gameforge_logs": {
            "type": "custom",
            "tokenizer": "standard",
            "filter": ["lowercase", "stop"]
          }
        }
      }
    },
    "mappings": {
      "properties": {
        "@timestamp": {
          "type": "date",
          "format": "strict_date_optional_time||epoch_millis"
        },
        "message": {
          "type": "text",
          "analyzer": "gameforge_logs",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        },
        "log": {
          "properties": {
            "level": {"type": "keyword"},
            "logger": {"type": "keyword"},
            "file": {
              "properties": {
                "path": {"type": "keyword"},
                "line": {"type": "integer"}
              }
            }
          }
        },
        "service": {
          "properties": {
            "name": {"type": "keyword"},
            "version": {"type": "keyword"},
            "environment": {"type": "keyword"}
          }
        },
        "container": {
          "properties": {
            "id": {"type": "keyword"},
            "name": {"type": "keyword"},
            "image": {
              "properties": {
                "name": {"type": "keyword"},
                "tag": {"type": "keyword"}
              }
            }
          }
        },
        "correlation_id": {"type": "keyword"},
        "trace_id": {"type": "keyword"},
        "span_id": {"type": "keyword"},
        "user_id": {"type": "keyword"},
        "session_id": {"type": "keyword"},
        "request": {
          "properties": {
            "id": {"type": "keyword"},
            "method": {"type": "keyword"},
            "url": {
              "type": "text",
              "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "path": {"type": "keyword"},
            "body_size": {"type": "long"}
          }
        },
        "response": {
          "properties": {
            "status_code": {"type": "integer"},
            "status_class": {"type": "keyword"},
            "body_size": {"type": "long"},
            "duration_ms": {"type": "float"}
          }
        },
        "error": {
          "properties": {
            "type": {"type": "keyword"},
            "message": {"type": "text"},
            "stack_trace": {"type": "text", "index": false},
            "code": {"type": "keyword"}
          }
        },
        "ai": {
          "properties": {
            "model": {"type": "keyword"},
            "inference_time_ms": {"type": "float"},
            "gpu_memory_mb": {"type": "long"},
            "batch_size": {"type": "integer"},
            "prompt_length": {"type": "integer"},
            "response_length": {"type": "integer"}
          }
        },
        "database": {
          "properties": {
            "query": {"type": "text", "index": false},
            "duration_ms": {"type": "float"},
            "rows_affected": {"type": "long"}
          }
        },
        "security": {
          "properties": {
            "event_type": {"type": "keyword"},
            "source_ip": {"type": "ip"},
            "user_agent": {
              "type": "text",
              "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "auth_result": {"type": "keyword"},
            "risk_score": {"type": "float"}
          }
        },
        "tags": {"type": "keyword"},
        "environment": {"type": "keyword"},
        "cluster": {"type": "keyword"}
      }
    }
  },
  "priority": 500,
  "_meta": {
    "description": "GameForge AI production logs template"
  }
}'

# ========================================================================
# Ingest Pipeline for Log Processing
# ========================================================================
echo "Creating ingest pipeline..."
curl -X PUT "elasticsearch:9200/_ingest/pipeline/gameforge-logs-pipeline" \
  -H 'Content-Type: application/json' \
  -d '{
  "description": "GameForge AI log processing pipeline",
  "processors": [
    {
      "set": {
        "field": "pipeline.name",
        "value": "gameforge-logs-pipeline"
      }
    },
    {
      "date": {
        "field": "@timestamp",
        "formats": [
          "ISO8601",
          "yyyy-MM-dd'\''T'\''HH:mm:ss.SSSZ",
          "yyyy-MM-dd'\''T'\''HH:mm:ssZ",
          "yyyy-MM-dd HH:mm:ss.SSS",
          "epoch_millis"
        ],
        "on_failure": [
          {
            "set": {
              "field": "@timestamp",
              "value": "{{_ingest.timestamp}}"
            }
          }
        ]
      }
    },
    {
      "grok": {
        "field": "message",
        "patterns": [
          "%{TIMESTAMP_ISO8601:log.timestamp} %{LOGLEVEL:log.level} %{DATA:log.logger} - %{GREEDYDATA:log.message}",
          "\\[%{TIMESTAMP_ISO8601:log.timestamp}\\] %{LOGLEVEL:log.level}: %{GREEDYDATA:log.message}"
        ],
        "ignore_failure": true
      }
    },
    {
      "script": {
        "description": "Extract correlation and trace IDs",
        "lang": "painless",
        "source": "if (ctx.message != null) { def requestIdPattern = /(?i)(?:request[_-]?id|correlation[_-]?id)[:\\s]*([a-f0-9-]{8,})/; def requestIdMatcher = requestIdPattern.matcher(ctx.message); if (requestIdMatcher.find()) { ctx.correlation_id = requestIdMatcher.group(1); } def traceIdPattern = /(?i)trace[_-]?id[:\\s]*([a-f0-9-]{8,})/; def traceIdMatcher = traceIdPattern.matcher(ctx.message); if (traceIdMatcher.find()) { ctx.trace_id = traceIdMatcher.group(1); } }"
      }
    },
    {
      "script": {
        "description": "Classify log events and add tags",
        "lang": "painless",
        "source": "def tags = new ArrayList(); def message = ctx.message != null ? ctx.message.toLowerCase() : \"\"; def level = ctx.log != null && ctx.log.level != null ? ctx.log.level.toLowerCase() : \"\"; if (level.equals(\"error\") || level.equals(\"fatal\")) { tags.add(\"error\"); tags.add(\"alert\"); } else if (level.equals(\"warn\") || level.equals(\"warning\")) { tags.add(\"warning\"); } if (message.contains(\"security\") || message.contains(\"auth\")) { tags.add(\"security\"); } if (message.contains(\"performance\") || message.contains(\"slow\")) { tags.add(\"performance\"); } if (message.contains(\"inference\") || message.contains(\"model\")) { tags.add(\"ai-ml\"); } if (tags.size() > 0) { ctx.tags = tags; }"
      }
    }
  ]
}'

# ========================================================================
# Create Initial Index and Alias
# ========================================================================
echo "Creating initial index..."
curl -X PUT "elasticsearch:9200/gameforge-logs-000001" \
  -H 'Content-Type: application/json' \
  -d '{
  "aliases": {
    "gameforge-logs": {
      "is_write_index": true
    }
  },
  "settings": {
    "index.lifecycle.name": "gameforge-logs-policy",
    "index.lifecycle.rollover_alias": "gameforge-logs"
  }
}'

echo "Elasticsearch log aggregation pipeline setup complete!"
echo "Log indices will be available at: gameforge-logs-*"
echo "Write alias: gameforge-logs"
echo "ILM policy: gameforge-logs-policy"